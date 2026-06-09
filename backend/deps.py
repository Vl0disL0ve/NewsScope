# -*- coding: utf-8 -*-
"""
FastAPI-зависимости (Dependency Injection).
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import Header, HTTPException
from backend.services.auth_service import AuthService


async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    Извлекает и проверяет JWT-токен из заголовка Authorization.
    Возвращает данные пользователя или выбрасывает 401.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Неверный формат токена")
    token = authorization.removeprefix("Bearer ")
    service = AuthService()
    user = await service.get_current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Токен недействителен или истёк")
    return user
