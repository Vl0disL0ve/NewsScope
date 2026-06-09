# -*- coding: utf-8 -*-
"""
ParserController — API-роуты для запуска парсеров новостей.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from backend.deps import get_current_user
from backend.services.parser_service import LentaParser, TelegramChannelParser

router = APIRouter(prefix="/api/parser", tags=["parser"])

class TgChannelRequest(BaseModel):
    channel: str = Field(..., min_length=1, description="Имя канала (@channel или channel)")


@router.post("/lenta")
async def parse_lenta(current_user: dict = Depends(get_current_user)):
    """Запуск парсера Lenta.ru — загружает свежие новости в БД."""
    parser = LentaParser()
    try:
        news = await parser.fetch_news()
        saved = await parser.save_news(news)
        return {
            "success": True,
            "total_fetched": len(news),
            "new_saved": saved,
            "message": f"Загружено {len(news)} новостей, добавлено {saved} новых"
        }
    except RuntimeError as e:
        # Если парсер Lenta не сработал — добавляем демо-новости
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/tg")
async def parse_telegram(
    data: TgChannelRequest,
    current_user: dict = Depends(get_current_user),
):
    """Запуск парсера Telegram-канала — загружает сообщения из указанного канала."""
    import backend.config as cfg
    if not cfg.TG_API_ID or not cfg.TG_API_HASH:
        raise HTTPException(
            status_code=400,
            detail="Telegram API не настроен. Укажите TG_API_ID и TG_API_HASH в .env"
        )

    channel = data.channel.strip()
    if not channel.startswith("@"):
        channel = "@" + channel

    parser = TelegramChannelParser()
    try:
        news = await parser.fetch_channel_news(channel, limit=30)
        if not news:
            return {"success": True, "total_fetched": 0, "new_saved": 0,
                    "message": f"Нет новых сообщений в {channel}"}
        saved = await parser.save_news(news)
        return {
            "success": True,
            "total_fetched": len(news),
            "new_saved": saved,
            "message": f"Загружено {len(news)} сообщений из {channel}, добавлено {saved} новых"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга Telegram: {e}")
