from sqlalchemy import Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base
from datetime import datetime

class UserHistory(Base):
    __tablename__ = "user_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CLUSTER, SEARCH, TTS, PLOT, CHRONOLOGY
    action_params: Mapped[str] = mapped_column(Text, nullable=True)  # JSON
    result_preview: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())