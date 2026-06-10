# TODO: Добавить поддержку сессий с JWT токенами
# Проблема: Сейчас авторизация без сохранения состояния (stateless)
# Решение: При успешном логине генерировать JWT токен и возвращать клиенту
# В вебе хранить в cookies/localStorage, в TG в памяти
# Приоритет: СРЕДНИЙ (для веб-интерфейса понадобится)

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.models.entry_log import EntryLog
from datetime import datetime, timedelta
from app.config import config

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def login(self, login: str, password: str, source: str = "WEB") -> dict:
        """Проверяет логин/пароль, возвращает результат"""
        # Ищем пользователя
        stmt = select(User).where(User.login == login)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "message": "Неверный логин или пароль"}
        
        # Проверка блокировки
        if user.is_blocked and user.block_until and user.block_until > datetime.now():
            remaining = (user.block_until - datetime.now()).seconds // 60
            return {"success": False, "message": f"Аккаунт заблокирован на {remaining} минут"}
        
        # Проверка пароля
        if not check_password_hash(user.password_hash, password):
            # Увеличиваем счётчик неудач
            user.failed_attempts += 1
            
            if user.failed_attempts >= config.MAX_LOGIN_ATTEMPTS:
                user.is_blocked = True
                user.block_until = datetime.now() + timedelta(minutes=config.BLOCK_MINUTES)
                await self.db.commit()
                return {"success": False, "message": f"Слишком много попыток. Блокировка на {config.BLOCK_MINUTES} минут"}
            
            await self.db.commit()
            return {"success": False, "message": "Неверный логин или пароль"}
        
        # Успешный вход - сбрасываем счётчики
        user.failed_attempts = 0
        user.is_blocked = False
        user.block_until = None
        
        # Логируем вход
        entry_log = EntryLog(user_id=user.id, source=source)
        self.db.add(entry_log)
        await self.db.commit()
        
        return {
            "success": True,
            "user_id": user.id,
            "login": user.login,
            "role": user.role
        }
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Хэширует пароль"""
        return generate_password_hash(password)