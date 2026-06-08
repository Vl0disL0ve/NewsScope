import torch
import faiss
import edge_tts
from sentence_transformers import SentenceTransformer

import aiohttp

import os
import asyncio
import numpy as np
from typing import List, Dict


# ───────── КОНФИГУРАЦИЯ ─────────
EMBEDDING_MODEL = "ai-forever/FRIDA"
EMBEDDING_MODEL_PATH = f"{os.getcwd()}/ml_models/{EMBEDDING_MODEL}"

LLM_URL = "http://localhost:11434/api/chat"
LLM_MODEL = "gemma4:12b"
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
MAX_SUMMARY_TOKENS = 2048
LLM_TOTAL_TIMEOUT = 200
LLM_CONNECT_TIMEOUT = 30

SPEAKER_VOICE = "ru-RU-DmitryNeural"
# ────────────────────────────────

class SummaryService:
    def __init__(self):
        self.set_embeddings_model()
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        emb = self.embedding_model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        return emb.astype(np.float32)
    
    def set_embeddings_model(self):
        if not os.path.exists(EMBEDDING_MODEL_PATH):
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
            self.embedding_model.save(EMBEDDING_MODEL_PATH)
        else:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_PATH, device=DEVICE)
    
    def cluster_with_faiss(self, embeddings: np.ndarray, k: int) -> Dict[int, List[int]]:
        """Группирует векторы через FAISS k-means, возвращает {cluster_id: [idx_news, ...]}"""
        d = embeddings.shape[1]
        
        kmeans = faiss.Clustering(d, k)
        kmeans.niter = 20
        kmeans.verbose = False
        kmeans.seed = 42
        kmeans.max_points_per_centroid = 1000000
        
        index = faiss.IndexFlatIP(d)
        faiss.normalize_L2(embeddings)
        kmeans.train(embeddings, index)
        
        _, assignments = index.search(embeddings, 1)
        
        clusters: Dict[int, List[int]] = {i: [] for i in range(k)}
        for idx, cluster_id in enumerate(assignments.ravel()):
            clusters[cluster_id].append(idx)
            
        return {cid: indices for cid, indices in clusters.items() if indices}
    
    async def summarize_with_llm(self, text: str) -> str:
        sys_prompt = (
            "Ты — ассистент, который кратко пересказывает тексты на русском языке."
            "Отвечай ТОЛЬКО на русском языке."
            "Ответ должен быть из 2-4 предложений, только пересказ, без лишних слов."
        )
        
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": sys_prompt
                },
                {
                    "role": "user",
                    "content": f"Кратко перескажи этот текст, сохрани главную мысль:\n\n{text}"
                }
            ],
            "stream": False,
            "options": {
                "num_predict": MAX_SUMMARY_TOKENS,
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 64,
                "think": True
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    LLM_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=LLM_TOTAL_TIMEOUT,
                                                  connect=LLM_CONNECT_TIMEOUT)
                ) as response:
                    if response.status != 200:
                        return f"Ошибка HTTP: {response.status}"
                    
                    result = await response.json()
                    summary = result["message"]["content"].strip()
                    
                    if summary:
                        return summary
                    else:
                        return "Ошибка: Пустой ответ от модели"
                        
            except Exception as e:
                return f"Ошибка: {e}"


class TTSService:
    def __init__(self):
        pass

    async def text_to_speech(self, text: str, cluster_id: int, user_dir: str) -> str:
        """Преобразует текст в речь, сохраняет и возвращает путь к аудио файлу"""
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        filename = f"{user_dir}/summary_{cluster_id}.mp3"

        communicate = edge_tts.Communicate(text, SPEAKER_VOICE)
        await communicate.save(filename)
        return filename