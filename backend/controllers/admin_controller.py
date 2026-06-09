# -*- coding: utf-8 -*-
"""
AdminController — административные API-роуты.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import os

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional

from database.init_db import SessionLocal
from database.models import User, EntryLog, ActionLog, Cluster, News
from sqlalchemy import select, func, cast, Date, extract
from backend.deps import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _require_admin(current_user: dict):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return current_user


@router.get("/stats/visits")
async def visit_stats(
    interval: str = Query("day", description="day / week / month / custom"),
    user_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Статистика посещений с поддержкой почасовой детализации."""
    await _require_admin(current_user)

    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    # Автодиапазон
    if not dt_from and not dt_to:
        now = datetime.now(timezone.utc)
        if interval == "day":
            dt_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
            dt_to = now
        elif interval == "week":
            dt_from = now - timedelta(days=7)
            dt_to = now
        elif interval == "month":
            dt_from = now - timedelta(days=30)
            dt_to = now

    async with SessionLocal() as db:
        if interval == "day":
            # Почасовая детализация
            stmt = select(
                extract("hour", EntryLog.visit_time).label("hour"),
                func.count(EntryLog.entry_id).label("count"),
            )
            if user_id:
                stmt = stmt.where(EntryLog.user_id == user_id)
            if dt_from:
                stmt = stmt.where(EntryLog.visit_time >= dt_from)
            if dt_to:
                stmt = stmt.where(EntryLog.visit_time <= dt_to)
            stmt = stmt.group_by(extract("hour", EntryLog.visit_time)).order_by(
                extract("hour", EntryLog.visit_time)
            )
            rows = (await db.execute(stmt)).all()
            return [
                {"label": f"{int(row.hour):02d}:00", "value": row.count}
                for row in rows
            ]
        else:
            # Подневная детализация
            stmt = select(
                cast(EntryLog.visit_time, Date).label("date"),
                func.count(EntryLog.entry_id).label("count"),
            )
            if user_id:
                stmt = stmt.where(EntryLog.user_id == user_id)
            if dt_from:
                stmt = stmt.where(EntryLog.visit_time >= dt_from)
            if dt_to:
                stmt = stmt.where(EntryLog.visit_time <= dt_to)
            stmt = stmt.group_by(cast(EntryLog.visit_time, Date)).order_by(
                cast(EntryLog.visit_time, Date)
            )
            rows = (await db.execute(stmt)).all()
            return [
                {"label": str(row.date), "value": row.count}
                for row in rows
            ]


@router.get("/stats/users")
async def user_stats(
    interval: str = Query("month"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Статистика регистраций новых пользователей."""
    await _require_admin(current_user)

    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    if not dt_from and not dt_to:
        now = datetime.now(timezone.utc)
        if interval == "day":
            dt_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
            dt_to = now
        elif interval == "week":
            dt_from = now - timedelta(days=7)
            dt_to = now
        elif interval == "month":
            dt_from = now - timedelta(days=30)
            dt_to = now

    async with SessionLocal() as db:
        stmt = select(
            cast(User.created_at, Date).label("date"),
            func.count(User.user_id).label("count"),
        )
        if dt_from:
            stmt = stmt.where(User.created_at >= dt_from)
        if dt_to:
            stmt = stmt.where(User.created_at <= dt_to)
        stmt = stmt.group_by(cast(User.created_at, Date)).order_by(
            cast(User.created_at, Date)
        )
        rows = (await db.execute(stmt)).all()

    return [
        {"label": str(row.date), "value": row.count}
        for row in rows
    ]


@router.get("/stats/database")
async def database_stats(current_user: dict = Depends(get_current_user)):
    """Общая статистика БД + объём пользовательских данных."""
    await _require_admin(current_user)

    async with SessionLocal() as db:
        users_count = (await db.execute(select(func.count(User.user_id)))).scalar()
        news_count = (await db.execute(select(func.count(News.news_id)))).scalar()
        clusters_count = (await db.execute(select(func.count(Cluster.cluster_id)))).scalar()
        actions_count = (await db.execute(select(func.count(ActionLog.action_id)))).scalar()

    # Объём пользовательских данных (data/)
    data_dir = _project_root / "data"
    user_data_size_mb = 0
    if data_dir.exists():
        total_bytes = sum(
            f.stat().st_size for f in data_dir.rglob("*") if f.is_file()
        )
        user_data_size_mb = round(total_bytes / (1024 * 1024), 2)

    # Свободное место на диске
    try:
        import shutil
        disk_usage = shutil.disk_usage(str(_project_root))
        disk_total_gb = round(disk_usage.total / (1024**3), 1)
        disk_free_gb = round(disk_usage.free / (1024**3), 1)
    except Exception:
        disk_total_gb = 0
        disk_free_gb = 0

    return {
        "users": users_count,
        "news": news_count,
        "clusters": clusters_count,
        "actions": actions_count,
        "user_data_mb": user_data_size_mb,
        "disk_total_gb": disk_total_gb,
        "disk_free_gb": disk_free_gb,
    }


@router.get("/stats/actions")
async def action_stats(
    action_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Статистика типов действий."""
    await _require_admin(current_user)

    async with SessionLocal() as db:
        stmt = select(
            ActionLog.action_type,
            func.count(ActionLog.action_id).label("count"),
        )
        if action_type:
            stmt = stmt.where(ActionLog.action_type == action_type)
        stmt = stmt.group_by(ActionLog.action_type).order_by(ActionLog.action_type)
        rows = (await db.execute(stmt)).all()

    return [
        {"label": row.action_type, "value": row.count}
        for row in rows
    ]


@router.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
):
    """Поиск пользователей по логину."""
    await _require_admin(current_user)

    async with SessionLocal() as db:
        stmt = select(User).where(User.login.ilike(f"%{q}%")).limit(20)
        users = (await db.execute(stmt)).scalars().all()
        return [
            {"user_id": u.user_id, "login": u.login, "role": u.role}
            for u in users
        ]
