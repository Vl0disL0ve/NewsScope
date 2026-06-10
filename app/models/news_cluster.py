from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

class NewsCluster(Base):
    __tablename__ = "news_clusters"
    
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news.id", ondelete="CASCADE"), primary_key=True)
    cluster_id: Mapped[int] = mapped_column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True)
    
    # Связи
    news = relationship("News")
    cluster = relationship("Cluster", back_populates="news_items")