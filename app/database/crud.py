# TODO: Добавить каскадное удаление через foreign keys
# Проблема: При удалении пользователя нужно вручную удалять связанные записи
# Решение: В модели User добавить cascade="all, delete-orphan" в relationship
# ИЛИ использовать ON DELETE CASCADE в БД
# Сейчас удаление работает через явные delete() запросы

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.news import News
from app.models.cluster import Cluster
from app.models.news_cluster import NewsCluster
from app.models.user_history import UserHistory
from app.models.entry_log import EntryLog


class UserCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_login(self, login: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.login == login))
        return result.scalar_one_or_none()
    
    async def get_by_tg_id(self, tg_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()
    
    async def create(self, login: str, password_hash: str, role: str = "user", tg_id: int = None) -> User:
        user = User(login=login, password_hash=password_hash, role=role, tg_id=tg_id)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        # Создаём пустые настройки для пользователя
        settings = UserSettings(user_id=user.id)
        self.db.add(settings)
        await self.db.commit()
        
        return user
    
    async def update_tg_id(self, user_id: int, tg_id: int):
        user = await self.get_by_id(user_id)
        if user:
            user.tg_id = tg_id
            await self.db.commit()
    
    async def get_all_users(self) -> List[User]:
        result = await self.db.execute(select(User))
        return result.scalars().all()
    
    async def delete(self, user_id: int):
        await self.db.execute(delete(User).where(User.id == user_id))
        await self.db.commit()


class SettingsCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, user_id: int) -> Optional[UserSettings]:
        result = await self.db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()
    
    async def update(self, user_id: int, **kwargs):
        settings = await self.get(user_id)
        if settings:
            for key, value in kwargs.items():
                if hasattr(settings, key):
                    if key == "selected_channels" and isinstance(value, list):
                        value = json.dumps(value)
                    setattr(settings, key, value)
            await self.db.commit()
    
    async def get_selected_channels(self, user_id: int) -> List[str]:
        settings = await self.get(user_id)
        if settings and settings.selected_channels:
            return json.loads(settings.selected_channels)
        return []
    
    async def get_num_clusters(self, user_id: int) -> int:
        settings = await self.get(user_id)
        return settings.num_clusters if settings else 5


class NewsCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def add(self, published_at: datetime, channel: str, news_body: str, 
                  news_link: str, source: str, views: int = 0, 
                  forwarded: int = 0, subject: str = None) -> News:
        news = News(
            published_at=published_at,
            channel=channel,
            news_body=news_body,
            news_link=news_link,
            source=source,
            views=views,
            forwarded=forwarded,
            subject=subject
        )
        self.db.add(news)
        await self.db.commit()
        await self.db.refresh(news)
        return news
    
    async def exists_by_link(self, news_link: str) -> bool:
        result = await self.db.execute(select(News).where(News.news_link == news_link))
        return result.scalar_one_or_none() is not None
    
    async def get_news_for_period(self, start_date: datetime, end_date: datetime, 
                                    channels: List[str] = None) -> List[News]:
        query = select(News).where(
            and_(
                News.published_at >= start_date,
                News.published_at <= end_date
            )
        )
        if channels:
            query = query.where(News.channel.in_(channels))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_all_sources(self) -> List[str]:
        result = await self.db.execute(select(News.channel).distinct())
        return result.scalars().all()


class ClusterCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, topic: str, summary: str, 
                     news_ids: List[int], news_sources: List[str],
                     period_start: datetime, period_end: datetime) -> Cluster:
        # Создаём кластер
        cluster = Cluster(
            user_id=user_id,
            topic=topic,
            summary=summary,
            news_count=len(news_ids),
            news_sources=json.dumps(news_sources),
            period_start=period_start,
            period_end=period_end
        )
        self.db.add(cluster)
        await self.db.flush()  # Получаем cluster.id, но не коммитим
        
        # Связываем новости с кластером (только уникальные пары)
        existing_pairs = await self.db.execute(
            select(NewsCluster).where(
                and_(
                    NewsCluster.news_id.in_(news_ids),
                    NewsCluster.cluster_id == cluster.id
                )
            )
        )
        existing = {(nc.news_id, nc.cluster_id) for nc in existing_pairs.scalars()}
        
        for news_id in set(news_ids):  # Убираем дубликаты
            if (news_id, cluster.id) not in existing:
                nc = NewsCluster(news_id=news_id, cluster_id=cluster.id)
                self.db.add(nc)
        
        await self.db.commit()
        await self.db.refresh(cluster)
        
        return cluster    
 
    async def get_user_clusters(self, user_id: int) -> List[Cluster]:
        result = await self.db.execute(
            select(Cluster).where(Cluster.user_id == user_id).order_by(Cluster.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_by_id(self, cluster_id: int) -> Optional[Cluster]:
        result = await self.db.execute(
            select(Cluster).where(Cluster.id == cluster_id).options(selectinload(Cluster.news_items))
        )
        return result.scalar_one_or_none()
    
    async def update_audio_path(self, cluster_id: int, audio_path: str):
        await self.db.execute(
            update(Cluster).where(Cluster.id == cluster_id).values(audio_path=audio_path)
        )
        await self.db.commit()
    
    async def update_plot_path(self, cluster_id: int, plot_path: str):
        await self.db.execute(
            update(Cluster).where(Cluster.id == cluster_id).values(plot_path=plot_path)
        )
        await self.db.commit()
    
    async def update_chronology_path(self, cluster_id: int, chronology_path: str):
        await self.db.execute(
            update(Cluster).where(Cluster.id == cluster_id).values(chronology_path=chronology_path)
        )
        await self.db.commit()


class HistoryCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def add(self, user_id: int, action_type: str, action_params: Dict = None, result_preview: str = None):
        history = UserHistory(
            user_id=user_id,
            action_type=action_type,
            action_params=json.dumps(action_params) if action_params else None,
            result_preview=result_preview
        )
        self.db.add(history)
        await self.db.commit()
    
    async def get_user_history(self, user_id: int, limit: int = 50) -> List[UserHistory]:
        result = await self.db.execute(
            select(UserHistory)
            .where(UserHistory.user_id == user_id)
            .order_by(UserHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def clear_user_history(self, user_id: int):
        await self.db.execute(delete(UserHistory).where(UserHistory.user_id == user_id))
        await self.db.commit()


class StatsCRUD:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_visits_by_period(self, start_date: datetime, end_date: datetime, 
                                     user_id: int = None) -> List[tuple]:
        query = select(
            func.date(EntryLog.visit_time).label('date'),
            func.count(EntryLog.id).label('count')
        ).where(
            and_(
                EntryLog.visit_time >= start_date,
                EntryLog.visit_time <= end_date
            )
        )
        if user_id:
            query = query.where(EntryLog.user_id == user_id)
        query = query.group_by(func.date(EntryLog.visit_time))
        
        result = await self.db.execute(query)
        return result.all()
    
    async def get_new_users_by_period(self, start_date: datetime, end_date: datetime) -> List[tuple]:
        result = await self.db.execute(
            select(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            )
            .where(and_(User.created_at >= start_date, User.created_at <= end_date))
            .group_by(func.date(User.created_at))
        )
        return result.all()
    
    async def get_db_stats(self) -> Dict:
        # Количество пользователей
        users_count_result = await self.db.execute(select(func.count(User.id)))
        users_count = users_count_result.scalar()
        
        # Количество новостей
        news_count_result = await self.db.execute(select(func.count(News.id)))
        news_count = news_count_result.scalar()
        
        # Количество кластеров
        clusters_count_result = await self.db.execute(select(func.count(Cluster.id)))
        clusters_count = clusters_count_result.scalar()
        
        return {
            "users_count": users_count,
            "news_count": news_count,
            "clusters_count": clusters_count,
            "db_size_mb": 0  # Потом добавим
        }