# -*- coding: utf-8 -*-
"""
Скрипт первичного заполнения БД тестовыми данными.
Создаёт пользователей: admin/admin (админ) и user/user (обычный).
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import asyncio
import bcrypt as _bcrypt
from database.init_db import SessionLocal
from database.models import User
from sqlalchemy import select


async def seed():
    print("🌱 Заполнение БД тестовыми данными...")
    async with SessionLocal() as db:
        # Создаём админа
        stmt = select(User).where(User.login == "admin")
        admin = (await db.execute(stmt)).scalar_one_or_none()
        if not admin:
            admin = User(
                login="admin",
                password=_bcrypt.hashpw(b"admin", _bcrypt.gensalt()).decode(),
                role="admin",
                directory="users/admin",
            )
            db.add(admin)
            print("  ✅ Администратор: admin / admin")
        else:
            print("  ⏭️  Администратор уже существует")

        # Создаём обычного пользователя
        stmt = select(User).where(User.login == "user")
        user = (await db.execute(stmt)).scalar_one_or_none()
        if not user:
            user = User(
                login="user",
                password=_bcrypt.hashpw(b"user", _bcrypt.gensalt()).decode(),
                role="user",
                directory="users/user",
            )
            db.add(user)
            print("  ✅ Пользователь: user / user")
        else:
            print("  ⏭️  Пользователь уже существует")

        await db.commit()

    print("🌱 Готово!")


if __name__ == "__main__":
    asyncio.run(seed())
