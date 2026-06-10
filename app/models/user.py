from sqlalchemy import String, Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")  # admin / user
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=True)
    tg_username: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Безопасность
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Мета
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<User {self.login} ({self.role})>"