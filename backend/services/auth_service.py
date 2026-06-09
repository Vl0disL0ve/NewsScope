# -*- coding: utf-8 -*-
"""
AuthService — бизнес-логика аутентификации и управления пользователями.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import jwt, JWTError

# ─── Добавляем корень проекта в sys.path ───
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import backend.config as cfg
from database.init_db import SessionLocal
from database.models import User, UserSession, EntryLog
from sqlalchemy import select


class AuthService:
    """Сервис аутентификации: регистрация, вход, выход, проверка токенов."""

    @staticmethod
    def _hash_password(password: str) -> str:
        """Хэширование пароля напрямую через bcrypt."""
        return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

    @staticmethod
    def _verify_password(plain: str, hashed: str) -> bool:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())

    @staticmethod
    def _create_token(user_id: int, role: str) -> str:
        """Создаёт JWT-токен."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role,
            "iat": now,
            "exp": now + timedelta(hours=cfg.SESSION_EXPIRE_HOURS),
        }
        return jwt.encode(payload, cfg.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Декодирует и проверяет JWT. Возвращает payload или None."""
        try:
            payload = jwt.decode(token, cfg.SECRET_KEY, algorithms=["HS256"])
            return payload
        except JWTError:
            return None

    # ─── Регистрация ──────────────────────────────────────────

    async def register(
        self, login: str, password: str, role: str = "user", tg_uuid: Optional[str] = None
    ) -> dict:
        """Регистрация нового пользователя."""
        async with SessionLocal() as db:
            # Проверка уникальности логина
            stmt = select(User).where(User.login == login)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                return {"success": False, "error": "Логин уже занят"}

            # Формируем директорию пользователя
            directory = f"users/{login}"

            new_user = User(
                login=login,
                password=self._hash_password(password),
                role=role,
                directory=directory,
                tg_uuid=tg_uuid,
                token_balance=0,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            # Логируем вход
            entry = EntryLog(user_id=new_user.user_id, entry_source="web")
            db.add(entry)
            await db.commit()

            token = self._create_token(new_user.user_id, new_user.role)
            return {
                "success": True,
                "user_id": new_user.user_id,
                "token": token,
                "role": new_user.role,
                "login": new_user.login,
            }

    # ─── Вход ─────────────────────────────────────────────────

    async def login(self, login: str, password: str) -> dict:
        """Аутентификация пользователя."""
        async with SessionLocal() as db:
            stmt = select(User).where(User.login == login)
            user = (await db.execute(stmt)).scalar_one_or_none()

            if not user or not self._verify_password(password, user.password):
                return {"success": False, "error": "Неверный логин или пароль"}

            # Логируем вход
            entry = EntryLog(user_id=user.user_id, entry_source="web")
            db.add(entry)
            await db.commit()

            token = self._create_token(user.user_id, user.role)
            return {
                "success": True,
                "user_id": user.user_id,
                "token": token,
                "role": user.role,
                "login": user.login,
                "token_balance": float(user.token_balance),
            }

    # ─── Проверка токена ──────────────────────────────────────

    async def get_current_user(self, token: str) -> Optional[dict]:
        """Возвращает данные пользователя по токену."""
        payload = self.decode_token(token)
        if payload is None:
            return None

        async with SessionLocal() as db:
            user_id = int(payload["sub"])
            user = await db.get(User, user_id)
            if user is None:
                return None
            return {
                "user_id": user.user_id,
                "login": user.login,
                "role": user.role,
                "token_balance": float(user.token_balance),
                "directory": user.directory,
                "tg_uuid": user.tg_uuid,
            }

    # ─── Telegram-вход ────────────────────────────────────────

    async def login_by_tg(self, tg_uuid: str) -> dict:
        """Вход/регистрация через Telegram UUID."""
        async with SessionLocal() as db:
            stmt = select(User).where(User.tg_uuid == tg_uuid)
            user = (await db.execute(stmt)).scalar_one_or_none()

            if not user:
                return {"success": False, "error": "Telegram-аккаунт не привязан"}

            entry = EntryLog(user_id=user.user_id, entry_source="tg")
            db.add(entry)
            await db.commit()

            token = self._create_token(user.user_id, user.role)
            return {
                "success": True,
                "user_id": user.user_id,
                "token": token,
                "role": user.role,
                "login": user.login,
            }

    # ─── Получение списка пользователей (для админа) ──────────

    async def get_users(self) -> list[dict]:
        """Возвращает список всех пользователей."""
        async with SessionLocal() as db:
            stmt = select(User).order_by(User.created_at.desc())
            users = (await db.execute(stmt)).scalars().all()
            return [
                {
                    "user_id": u.user_id,
                    "login": u.login,
                    "role": u.role,
                    "created_at": u.created_at.isoformat(),
                    "token_balance": float(u.token_balance),
                    "tg_uuid": u.tg_uuid,
                }
                for u in users
            ]

    # ─── Обновление баланса токенов ───────────────────────────

    async def update_token_balance(self, user_id: int, amount: float) -> dict:
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "Пользователь не найден"}
            user.token_balance += amount
            await db.commit()
            await db.refresh(user)
            return {
                "success": True,
                "user_id": user.user_id,
                "token_balance": float(user.token_balance),
            }
