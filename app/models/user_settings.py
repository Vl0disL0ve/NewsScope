from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    num_clusters: Mapped[int] = mapped_column(Integer, default=5)
    selected_channels: Mapped[str] = mapped_column(Text, default="[]")  # JSON массив
    period_start: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[DateTime] = mapped_column(DateTime, nullable=True)