import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from collections import defaultdict
import json
import os
from pathlib import Path

from app.config import config

class AIService:
    """Сервис для эмбеддингов и кластеризации новостей"""
    
    def __init__(self):
        self.model = None
        self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"  # Быстрая модель на CPU
        self._load_model()
    
    def _load_model(self):
        """Загружает модель SentenceTransformer"""
        model_path = config.ML_MODELS_DIR / self.model_name.replace('/', '_')
        
        try:
            if os.path.exists(model_path):
                self.model = SentenceTransformer(str(model_path))
                print(f"  ✅ Модель загружена из кэша: {self.model_name}")
            else:
                print(f"  📥 Загружаю модель {self.model_name} (первый раз может быть долго)...")
                self.model = SentenceTransformer(self.model_name)
                self.model.save(str(model_path))
                print(f"  ✅ Модель загружена и сохранена в кэш")
        except Exception as e:
            print(f"  ❌ Ошибка загрузки модели: {e}")
            raise
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Получает эмбеддинги для списка текстов"""
        if not texts:
            return np.array([])
        
        # Эмбеддинги нормализуются для cosine similarity
        embeddings = self.model.encode(
            texts, 
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32
        )
        return embeddings.astype(np.float32)
    
    def cluster_with_faiss(self, embeddings: np.ndarray, num_clusters: int) -> Dict[int, List[int]]:
        """
        Кластеризация эмбеддингов через FAISS k-means
        Возвращает: {cluster_id: [индексы_новостей]}
        """
        if embeddings.shape[0] == 0:
            return {}
        
        n_points = embeddings.shape[0]
        
        # Корректируем количество кластеров
        if num_clusters > n_points:
            num_clusters = max(2, n_points // 2)
        if num_clusters < 2:
            num_clusters = min(2, n_points)
        
        d = embeddings.shape[1]  # размерность эмбеддинга
        
        # FAISS k-means
        kmeans = faiss.Clustering(d, num_clusters)
        kmeans.niter = 20
        kmeans.verbose = False
        kmeans.seed = 42
        kmeans.min_points_per_centroid = 1
        
        # Индекс для обучения
        index = faiss.IndexFlatIP(d)
        
        # Нормализация уже есть, обучаем
        kmeans.train(embeddings, index)
        
        # Получаем центроиды
        centroids = faiss.vector_float_to_array(kmeans.centroids).reshape(num_clusters, d)
        
        # Поиск ближайших центроидов
        index_centroids = faiss.IndexFlatIP(d)
        index_centroids.add(centroids)
        _, assignments = index_centroids.search(embeddings, 1)
        
        # Формируем результат
        clusters = defaultdict(list)
        for idx, cluster_id in enumerate(assignments.ravel()):
            clusters[int(cluster_id)].append(idx)
        
        # Удаляем пустые кластеры
        return {cid: indices for cid, indices in clusters.items() if indices}
    
    def get_cluster_center(self, embeddings: np.ndarray, indices: List[int]) -> np.ndarray:
        """Возвращает центр кластера (среднее эмбеддингов)"""
        if not indices:
            return None
        cluster_embeddings = embeddings[indices]
        return np.mean(cluster_embeddings, axis=0)
    
    def find_similar_clusters(self, query_embedding: np.ndarray, cluster_centers: List[np.ndarray], k: int = 5) -> List[int]:
        """Находит k самых похожих кластеров по эмбеддингу запроса"""
        if not cluster_centers:
            return []
        
        centers_matrix = np.array(cluster_centers)
        
        # Нормализуем
        faiss.normalize_L2(centers_matrix)
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Поиск
        index = faiss.IndexFlatIP(centers_matrix.shape[1])
        index.add(centers_matrix)
        
        distances, indices = index.search(query_norm.reshape(1, -1), min(k, len(cluster_centers)))
        
        return indices[0].tolist()