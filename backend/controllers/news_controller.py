# -*- coding: utf-8 -*-
"""
NewsController — API-роуты для работы с новостями.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import APIRouter, HTTPException, Query, Depends
from backend.services.news_service import NewsService
from backend.deps import get_current_user
from datetime import datetime, timezone
from datetime import time as dt_time

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/")
async def list_news(
    source: Optional[str] = Query(None, description="Фильтр по источнику: tg / lenta"),
    subject: Optional[str] = Query(None, description="Фильтр по теме"),
    search: Optional[str] = Query(None, description="Поисковый запрос"),
    date_from: Optional[str] = Query(None, description="Дата с (ISO-формат)"),
    date_to: Optional[str] = Query(None, description="Дата по (ISO-формат)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Получение списка новостей с фильтрацией."""
    dt_from = None
    dt_to = None
    if date_from:
        dt_from_date = datetime.fromisoformat(date_from).date()
        dt_from = datetime.combine(dt_from_date, dt_time.min, tzinfo=timezone.utc)
    if date_to:
        dt_to_date = datetime.fromisoformat(date_to).date()
        dt_to = datetime.combine(dt_to_date, dt_time.max, tzinfo=timezone.utc)

    service = NewsService()
    results = await service.get_news(
        source=source,
        subject=subject,
        search_query=search,
        date_from=dt_from,
        date_to=dt_to,
        skip=skip,
        limit=limit,
    )

    return {
        "total": len(results),
        "news": results,
    }


@router.get("/sources")
async def get_sources(current_user: dict = Depends(get_current_user)):
    """Получение списка доступных каналов/источников."""
    service = NewsService()
    channels = await service.get_available_sources()
    return {"sources": channels}


@router.get("/{news_id}")
async def get_news_detail(
    news_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Получение детальной информации о новости."""
    service = NewsService()
    results = await service.get_news_by_ids([news_id])
    if not results:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return results[0]
