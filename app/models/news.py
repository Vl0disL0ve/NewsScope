from sqlalchemy import Integer, String, DateTime, Text, Integer as SQLInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base
from datetime import datetime

class News(Base):
    __tablename__ = "news"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    channel: Mapped[str] = mapped_column(String(200), nullable=False)  # название канала/автор
    news_body: Mapped[str] = mapped_column(Text, nullable=False)
    news_link: Mapped[str] = mapped_column(String(500), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    forwarded: Mapped[int] = mapped_column(Integer, default=0)
    subject: Mapped[str] = mapped_column(String(200), nullable=True)  # только для Lenta
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'TG' / 'LENTA'