import torch
import faiss
import edge_tts
from sentence_transformers import SentenceTransformer

import aiohttp
import hashlib
import pickle
import os
import asyncio
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Загружаем .env из корня проекта (явный путь, не зависит от CWD)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)


# ───────── КОНФИГУРАЦИЯ ─────────
EMBEDDING_MODEL = "ai-forever/FRIDA"
EMBEDDING_MODEL_PATH = f"{os.getcwd()}/ml_models/{EMBEDDING_MODEL}"

LLM_URL = os.getenv("LLM_URL", "http://localhost:11434/api/chat")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:12b")
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
MAX_SUMMARY_TOKENS = 2048
LLM_TOTAL_TIMEOUT = 200
LLM_CONNECT_TIMEOUT = 30

SPEAKER_VOICE = "ru-RU-DmitryNeural"

# Путь для кэша эмбеддингов
CACHE_DIR = Path(os.getcwd()) / "data" / "embeddings"
CACHE_FILE = CACHE_DIR / "embeddings_cache.pkl"
# ────────────────────────────────


class EmbeddingCache:
    """
    Кэш эмбеддингов на диске (pickle).
    Ключ — SHA256 от текста, значение — эмбеддинг (np.ndarray).
    """

    def __init__(self, cache_path: Path = CACHE_FILE):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, np.ndarray] = {}
        self._dirty = False
        self._load()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "rb") as f:
                    self._cache = pickle.load(f)
                print(f"  📦 Загружено {len(self._cache)} эмбеддингов из кэша")
            except Exception:
                self._cache = {}

    def save(self):
        if self._dirty:
            try:
                with open(self.cache_path, "wb") as f:
                    pickle.dump(self._cache, f)
                print(f"  💾 Сохранено {len(self._cache)} эмбеддингов в кэш")
                self._dirty = False
            except Exception as e:
                print(f"  ⚠️  Ошибка сохранения кэша эмбеддингов: {e}")

    def get(self, text: str) -> Optional[np.ndarray]:
        h = self._hash(text)
        return self._cache.get(h)

    def set(self, text: str, embedding: np.ndarray):
        h = self._hash(text)
        self._cache[h] = embedding
        self._dirty = True

    def get_or_compute(self, texts: List[str], compute_fn) -> np.ndarray:
        """
        Для списка текстов: проверяет кэш, для новых — вызывает compute_fn.
        compute_fn(texts_to_compute) -> np.ndarray эмбеддингов.
        Возвращает матрицу эмбеддингов для всех текстов.
        """
        n = len(texts)
        if n == 0:
            return np.array([], dtype=np.float32)

        # Определяем, какие тексты есть в кэше, а какие нужно вычислить
        indices_to_compute = []
        texts_to_compute = []
        results = [None] * n

        for i, text in enumerate(texts):
            cached = self.get(text)
            if cached is not None:
                results[i] = cached
            else:
                indices_to_compute.append(i)
                texts_to_compute.append(text)

        # Вычисляем новые эмбеддинги
        if texts_to_compute:
            print(f"  🧮 Вычисляю эмбеддинги для {len(texts_to_compute)} текстов...")
            computed = compute_fn(texts_to_compute)  # (m, dim)
            for idx, emb in zip(indices_to_compute, computed):
                results[idx] = emb
                self.set(texts[idx], emb)
            self.save()

        return np.array(results, dtype=np.float32)


class SummaryService:
    def __init__(self, load_embeddings: bool = True, llm_url: Optional[str] = None, llm_model: Optional[str] = None):
        self.llm_url = llm_url or LLM_URL
        self.llm_model = llm_model or LLM_MODEL
        if load_embeddings:
            self.set_embeddings_model()
            self.embedding_cache = EmbeddingCache()
        else:
            self.embedding_model = None
            self.embedding_cache = None

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        if self.embedding_model is None:
            raise RuntimeError("Embedding model not loaded (use load_embeddings=True)")
        def _compute(texts_chunk):
            emb = self.embedding_model.encode(
                texts_chunk, normalize_embeddings=True, show_progress_bar=True
            )
            return emb.astype(np.float32)
        return self.embedding_cache.get_or_compute(texts, _compute)
    
    def set_embeddings_model(self):
        if not os.path.exists(EMBEDDING_MODEL_PATH):
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
            self.embedding_model.save(EMBEDDING_MODEL_PATH)
        else:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_PATH, device=DEVICE)
    
    def cluster_with_faiss(self, embeddings: np.ndarray, k: int) -> Dict[int, List[int]]:
        """Группирует векторы через FAISS k-means, возвращает {cluster_id: [idx_news, ...]}"""
        n_points = embeddings.shape[0]
        d = embeddings.shape[1]

        # Если точек меньше чем k, уменьшаем k
        k = min(k, max(2, n_points - 1))

        # FAISS по умолчанию требует 39 точек на центроид — уменьшаем
        kmeans = faiss.Clustering(d, k)
        kmeans.niter = 20
        kmeans.verbose = False
        kmeans.seed = 42
        kmeans.min_points_per_centroid = 2
        kmeans.max_points_per_centroid = 1000000

        index = faiss.IndexFlatIP(d)
        faiss.normalize_L2(embeddings)
        kmeans.train(embeddings, index)
        
        _, assignments = index.search(embeddings, 1)
        
        clusters: Dict[int, List[int]] = {i: [] for i in range(k)}
        for idx, cluster_id in enumerate(assignments.ravel()):
            clusters[cluster_id].append(idx)
            
        return {cid: indices for cid, indices in clusters.items() if indices}

    async def summarize_with_llm(self, text: str):
        """
        Возвращает кортеж (title, summary).
        title — краткое название темы (2-5 слов),
        summary — краткий пересказ.
        """
        if not text or len(text.strip()) < 50:
            return ("Новости", "Недостаточно текста для анализа.")

        text = text.strip()[:3000]

        prompt = (
            "Прочитай следующие новости и выполни две задачи:\n"
            "1. Придумай краткое название темы (2-5 слов), которое объединяет эти новости.\n"
            "2. Сделай краткий пересказ на русском языке (2-4 предложения).\n\n"
            "Формат ответа строго:\n"
            "topic: Название темы\n\n"
            "Твой пересказ здесь\n\n"
            f"{text}"
        )

        payload = {
            "model": self.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "num_predict": MAX_SUMMARY_TOKENS,
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }

        try:
            print(f"[LLM] Пробую подключиться: {self.llm_url}, модель: {self.llm_model}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.llm_url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=LLM_TOTAL_TIMEOUT,
                                                  connect=LLM_CONNECT_TIMEOUT)
                ) as response:
                    if response.status != 200:
                        return ("Новости", f"Ошибка HTTP: {response.status}")
                    result = await response.json()
                    content = result.get("message", {}).get("content", "").strip()
                    # print(content[:150] + "..." if len(content) > 150 else content)

                    # Парсим topic и summary
                    title = "Новости"
                    summary = content
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.lower().startswith("topic:"):
                            title = stripped.split(":", 1)[1].strip()
                            rest = [ln for ln in lines[i+1:] if ln.strip()]
                            summary = "\n".join(rest).strip()
                            break
                        elif stripped.lower().startswith("пересказ:"):
                            summary = stripped.split(":", 1)[1].strip()

                    return (title, summary if summary else content)
        except aiohttp.ClientConnectorError as e:
            print(f"[LLM ERROR] ClientConnectorError к {self.llm_url}: {e}")
            return ("Новости", "LLM недоступен")
        except Exception as e:
            print(f"[LLM ERROR] {type(e).__name__}: {e}")
            return ("Новости", f"Ошибка: {e}")


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