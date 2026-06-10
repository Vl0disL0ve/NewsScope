from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.parser_service import ParserService
from app.database.session import get_db
from app.database.crud import NewsCRUD

router = APIRouter(prefix="/api/parser", tags=["parser"])

class TGChannelRequest(BaseModel):
    channel: str

@router.post("/tg")
async def parse_tg_channel(request: TGChannelRequest):
    parser_service = ParserService()
    news = await parser_service.parse_telegram([request.channel], limit=10)
    await parser_service.close()
    return {"success": True, "message": f"Загружено {len(news)} новостей", "count": len(news)}

@router.post("/all")
async def parse_all_sources(db: AsyncSession = Depends(get_db)):
    """Парсит все доступные источники и сохраняет новости"""
    parser_service = ParserService()
    
    # Список популярных Telegram-каналов
    tg_channels = ['rian_ru', 'rt_russian', 'kommersant', 'lenta_ru', 'tass_agency']
    
    results = {
        "telegram": {},
        "errors": []
    }
    
    # Парсим Telegram каналы
    for channel in tg_channels:
        try:
            news = await parser_service.parse_telegram([channel], limit=15)
            results["telegram"][channel] = len(news)
        except Exception as e:
            results["errors"].append(f"{channel}: {e}")
    
    await parser_service.close()
    
    # Получаем общее количество новостей в БД
    news_crud = NewsCRUD(db)
    sources = await news_crud.get_all_sources()
    
    return {
        "success": True,
        "message": "Парсинг завершён",
        "results": results,
        "total_news_in_db": len(sources) if sources else 0
    }