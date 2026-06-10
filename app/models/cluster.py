from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base
from datetime import datetime

class Cluster(Base):
    __tablename__ = "clusters"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    news_count: Mapped[int] = mapped_column(Integer, default=0)
    news_sources: Mapped[str] = mapped_column(Text, default="[]")  # JSON список источников
    
    # Пути к файлам
    audio_path: Mapped[str] = mapped_column(String(500), nullable=True)
    plot_path: Mapped[str] = mapped_column(String(500), nullable=True)
    chronology_path: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Период
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Связи
    news_items = relationship("NewsCluster", back_populates="cluster")