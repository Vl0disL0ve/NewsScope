# -*- coding: utf-8 -*-
"""
AuthController — API-роуты аутентификации (регистрация, вход, выход, профиль).
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from backend.services.auth_service import AuthService
from backend.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─── Pydantic-схемы ───────────────────────────────────────────

class RegisterRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=128)
    role: str = "user"
    tg_uuid: Optional[str] = None


class LoginRequest(BaseModel):
    login: str
    password: str


class TgLoginRequest(BaseModel):
    tg_uuid: str


class TokenBalanceRequest(BaseModel):
    user_id: int
    amount: float


# ─── Роуты ────────────────────────────────────────────────────

@router.post("/register")
async def register(data: RegisterRequest):
    """Регистрация нового пользователя."""
    service = AuthService()
    result = await service.register(
        login=data.login,
        password=data.password,
        role=data.role,
        tg_uuid=data.tg_uuid,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/login")
async def login(data: LoginRequest):
    """Вход пользователя."""
    service = AuthService()
    result = await service.login(login=data.login, password=data.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.post("/login/tg")
async def login_tg(data: TgLoginRequest):
    """Вход через Telegram UUID."""
    service = AuthService()
    result = await service.login_by_tg(tg_uuid=data.tg_uuid)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.get("/profile")
async def profile(current_user: dict = Depends(get_current_user)):
    """Получение профиля текущего пользователя."""
    return current_user


@router.post("/token-balance")
async def update_balance(
    data: TokenBalanceRequest,
    current_user: dict = Depends(get_current_user),
):
    """Обновление баланса токенов (только для admin)."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    service = AuthService()
    result = await service.update_token_balance(data.user_id, data.amount)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Список пользователей (только для admin)."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    service = AuthService()
    return await service.get_users()


# ─── Пользовательские настройки ──────────────────────────────

class SaveSettingsRequest(BaseModel):
    cluster_count: int = Field(default=10, ge=2, le=30)
    channels: list[str] = Field(default_factory=list)


@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Загрузка настроек пользователя с сервера."""
    import json
    settings_path = (
        _project_root / "data" / current_user["login"] / "settings.json"
    )
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"cluster_count": 10, "channels": []}


@router.post("/settings")
async def save_settings(
    data: SaveSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Сохранение настроек пользователя на сервер."""
    import json
    user_dir = _project_root / "data" / current_user["login"]
    user_dir.mkdir(parents=True, exist_ok=True)
    settings_path = user_dir / "settings.json"
    settings = {
        "cluster_count": data.cluster_count,
        "channels": data.channels,
    }
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "settings": settings}
