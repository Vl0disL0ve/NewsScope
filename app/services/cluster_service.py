from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from datetime import datetime
import json

from app.services.ai_service import AIService
from app.services.llm_service import LLMService
from app.database.crud import NewsCRUD, ClusterCRUD
from app.database.session import AsyncSessionLocal

class ClusterService:
    """Сервис для полного цикла кластеризации новостей"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.llm_service = LLMService()
    
    async def run_clustering(self, user_id: int, num_clusters: int, 
                             channels: List[str], start_date: datetime, 
                             end_date: datetime) -> Dict[str, Any]:
        """
        Выполняет кластеризацию новостей для пользователя
        """
        print(f"  🧮 Запуск кластеризации для user_id={user_id}, clusters={num_clusters}")
        
        async with AsyncSessionLocal() as db:
            # 1. Получаем новости из БД
            news_crud = NewsCRUD(db)
            news_list = await news_crud.get_news_for_period(start_date, end_date, channels)
            
            if not news_list:
                return {"success": False, "message": "Нет новостей за выбранный период"}
            
            print(f"  📰 Найдено новостей: {len(news_list)}")
            
            # 2. Извлекаем тексты и ID
            news_texts = [n.news_body for n in news_list]
            news_ids = [n.id for n in news_list]
            news_sources = list(set([n.channel for n in news_list]))
            
            # 3. Получаем эмбеддинги
            embeddings = self.ai_service.get_embeddings(news_texts)
            
            # 4. Кластеризация
            clusters = self.ai_service.cluster_with_faiss(embeddings, num_clusters)
            
            print(f"  📊 Создано кластеров: {len(clusters)}")
            
            # 5. Для каждого кластера генерируем тему и саммари
            cluster_crud = ClusterCRUD(db)
            results = []
            
            for cluster_id, news_indices in clusters.items():
                # Получаем тексты новостей в кластере
                cluster_news_texts = [news_texts[i] for i in news_indices]
                cluster_news_ids = [news_ids[i] for i in news_indices]
                
                # Генерируем тему и саммари через LLM
                topic, summary = await self.llm_service.generate_topic_and_summary(cluster_news_texts)
                
                # Сохраняем кластер в БД
                cluster = await cluster_crud.create(
                    user_id=user_id,
                    topic=topic,
                    summary=summary,
                    news_ids=cluster_news_ids,
                    news_sources=news_sources,
                    period_start=start_date,
                    period_end=end_date
                )
                
                results.append({
                    "cluster_id": cluster.id,
                    "topic": topic,
                    "summary": summary,
                    "news_count": len(cluster_news_ids),
                    "sources": news_sources
                })
            
            return {
                "success": True,
                "total_news": len(news_list),
                "num_clusters": len(clusters),
                "clusters": results
            }
    
    async def search_by_query(self, user_id: int, query: str) -> List[Dict]:
        """
        Поиск по ключевым словам через эмбеддинги
        """
        async with AsyncSessionLocal() as db:
            # Получаем все кластеры пользователя
            cluster_crud = ClusterCRUD(db)
            clusters = await cluster_crud.get_user_clusters(user_id)
            
            if not clusters:
                return []
            
            # Получаем эмбеддинг запроса
            query_embedding = self.ai_service.get_embeddings([query])[0]
            
            # Получаем эмбеддинги кластеров
            cluster_texts = [f"{c.topic} {c.summary}" for c in clusters]
            cluster_embeddings = self.ai_service.get_embeddings(cluster_texts)
            
            # Находим похожие кластеры
            similar_indices = self.ai_service.find_similar_clusters(
                query_embedding, list(cluster_embeddings), k=5
            )
            
            # Формируем результат
            results = []
            for idx in similar_indices:
                if idx < len(clusters):
                    c = clusters[idx]
                    results.append({
                        "cluster_id": c.id,
                        "topic": c.topic,
                        "summary": c.summary,
                        "news_count": c.news_count,
                        "relevance": 1.0 - idx * 0.1  # Приблизительная релевантность
                    })
            
            return results