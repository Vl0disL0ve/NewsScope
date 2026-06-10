from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.crud import NewsCRUD

router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/sources")
async def get_news_sources(db: AsyncSession = Depends(get_db)):
    news_crud = NewsCRUD(db)
    sources = await news_crud.get_all_sources()
    return {"sources": sources}