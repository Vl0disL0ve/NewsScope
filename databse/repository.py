from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import TypeVar, Generic, Type, Optional, List
import logging

from models import *


ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Базовый репозиторий с общими CRUD-методами"""
    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def create(self, obj_in: ModelType) -> ModelType:
        self.db.add(obj_in)
        try:
            self.db.commit()
            self.db.refresh(obj_in)  # Подтягивает ID, created_at, дефолты из БД
            return obj_in
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, obj_id: int) -> Optional[ModelType]:
        return self.db.get(self.model, obj_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return self.db.scalars(stmt).all()

    def delete_by_id(self, obj_id: int) -> bool:
        obj = self.get_by_id(obj_id)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_login(self, login: str) -> Optional[User]:
        stmt = select(User).where(User.login == login)
        return self.db.scalars(stmt).first()

    def get_by_directory(self, directory: str) -> Optional[User]:
        stmt = select(User).where(User.directory == directory)
        return self.db.scalars(stmt).first()

    def update_token_balance(self, user_id: int, amount: float) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            user.token_balance += amount
            self.db.commit()
            self.db.refresh(user)
        return user

    def update_login(self, user_id: int, new_login: str) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            user.login = new_login
            self.db.commit()
            self.db.refresh(user)
        return user


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self, db: Session):
        super().__init__(db, UserSession)

    def get_by_token(self, token: str) -> Optional[UserSession]:
        stmt = select(UserSession).where(UserSession.token == token)
        return self.db.scalars(stmt).first()

    def get_active_by_user(self, user_id: int, current_time: datetime) -> Optional[UserSession]:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.expires_at > current_time
        )
        return self.db.scalars(stmt).first()

    def delete_by_user(self, user_id: int) -> int:
        stmt = select(UserSession).where(UserSession.user_id == user_id)
        sessions = self.db.scalars(stmt).all()
        count = len(sessions)
        for s in sessions:
            self.db.delete(s)
        self.db.commit()
        return count


class NewsRepository(BaseRepository[News]):
    def __init__(self, db: Session):
        super().__init__(db, News)

    def get_by_source(self, source: str, skip: int = 0, limit: int = 50) -> List[News]:
        stmt = (select(News)
                .where(News.news_source == source)
                .order_by(News.published_at.desc())
                .offset(skip)
                .limit(limit))
        return self.db.scalars(stmt).all()

    def get_by_subject(self, subject: str, skip: int = 0, limit: int = 50) -> List[News]:
        stmt = (select(News)
                .where(News.subject.ilike(f"%{subject}%"))  # Регистронезависимый поиск
                .offset(skip)
                .limit(limit))
        return self.db.scalars(stmt).all()

class ClusterRepository(BaseRepository[Cluster]):
    def __init__(self, db: Session):
        super().__init__(db, Cluster)

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 20):
        stmt = select(Cluster).where(Cluster.user_id == user_id).offset(skip).limit(limit)
        return self.db.scalars(stmt).all()

    def get_with_news(self, cluster_id: int) -> Optional[Cluster]:
        """Загружает кластер + связанные новости одним запросом (избегает N+1)"""
        stmt = (select(Cluster)
                .options(joinedload(Cluster.news_items))
                .where(Cluster.cluster_id == cluster_id))
        return self.db.scalars(stmt).first()

    def link_news(self, cluster_id: int, news_id: int) -> bool:
        cluster = self.get_by_id(cluster_id)
        news = self.db.get(News, news_id)
        if cluster and news and news not in cluster.news_items:
            cluster.news_items.append(news)
            self.db.commit()
            return True
        return False

    def unlink_news(self, cluster_id: int, news_id: int) -> bool:
        cluster = self.get_by_id(cluster_id)
        news = self.db.get(News, news_id)
        if cluster and news and news in cluster.news_items:
            cluster.news_items.remove(news)
            self.db.commit()
            return True
        return False

    def append_source(self, cluster_id: int, source: str) -> Optional[Cluster]:
        cluster = self.get_by_id(cluster_id)
        if cluster and source not in cluster.news_sources:
            cluster.news_sources.append(source)
            self.db.commit()
            self.db.refresh(cluster)
        return cluster


class EntryLogRepository(BaseRepository[EntryLog]):
    def __init__(self, db: Session):
        super().__init__(db, EntryLog)

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[EntryLog]:
        stmt = (select(EntryLog)
                .where(EntryLog.user_id == user_id)
                .order_by(EntryLog.visit_time.desc())
                .offset(skip)
                .limit(limit))
        return self.db.scalars(stmt).all()

class ActionLogRepository(BaseRepository[ActionLog]):
    def __init__(self, db: Session):
        super().__init__(db, ActionLog)

    def get_by_cluster(self, cluster_id: int) -> List[ActionLog]:
        stmt = select(ActionLog).where(ActionLog.cluster_id == cluster_id).order_by(ActionLog.action_time.desc())
        return self.db.scalars(stmt).all()