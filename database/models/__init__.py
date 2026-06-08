# -*- coding: utf-8 -*-
from sqlalchemy import (
    Text, Integer, DateTime, Numeric, ForeignKey, 
    CheckConstraint, ARRAY, text
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'user'"))
    login: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    directory: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    tg_uuid: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    token_balance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, server_default=text("0"))

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    entry_logs: Mapped[list["EntryLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    clusters: Mapped[list["Cluster"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="role_check"),
    )

class UserSession(Base):
    __tablename__ = "sessions"
    
    session_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")

class EntryLog(Base):
    __tablename__ = "entry_log"
    
    entry_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    visit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    entry_source: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship(back_populates="entry_logs")

    __table_args__ = (
        CheckConstraint("entry_source IN ('web', 'tg')", name="source_check"),
    )

class Cluster(Base):
    __tablename__ = "clusters"
    
    cluster_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plot_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chronology_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    news_sources: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="clusters")
    actions: Mapped[list["ActionLog"]] = relationship(back_populates="cluster", cascade="all, delete-orphan")
    news_items: Mapped[list["News"]] = relationship(secondary="news_clusters", back_populates="clusters")

class ActionLog(Base):
    __tablename__ = "actions_log"
    
    action_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.cluster_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    action_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    action_type: Mapped[str] = mapped_column(Text, nullable=False)

    cluster: Mapped["Cluster"] = relationship(back_populates="actions")

class News(Base):
    __tablename__ = "news"
    
    news_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    news_body: Mapped[str] = mapped_column(Text, nullable=False)
    news_link: Mapped[str] = mapped_column(Text, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    forwarded: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    subject: Mapped[Optional[str]] = mapped_column("subject", Text, nullable=True)
    news_source: Mapped[str] = mapped_column(Text, nullable=False)

    clusters: Mapped[list["Cluster"]] = relationship(secondary="news_clusters", back_populates="news_items")

    __table_args__ = (
        CheckConstraint("news_source IN ('tg', 'lenta')", name="news_source_check"),
    )

class NewsCluster(Base):
    """Ассоциативная таблица для связи Cluster <-> News"""
    __tablename__ = "news_clusters"
    
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.cluster_id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    news_id: Mapped[int] = mapped_column(ForeignKey("news.news_id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)


__all__ = ["Base", "User", "UserSession", "EntryLog", "Cluster", "ActionLog", "News", "NewsCluster"]