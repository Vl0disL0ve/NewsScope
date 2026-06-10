# TODO: Добавить поддержку большего количества каналов
# Проблема: Некоторые каналы требуют подписки или имеют ограничения
# Решение: Добавить обработку приватных каналов через invite link
#
# TODO: Добавить обработку медиафайлов
# Сейчас парсится только текст, нужно сохранять фото/видео
#
# TODO: Улучшить авторизацию
# Сейчас требуется ручной ввод кода, добавить автоматическое хранение сессии

"""
Скрипт для авторизации в Telegram (запустить один раз)
python -m app.services.parser.telegram_auth
"""

import asyncio
from telethon import TelegramClient
from app.config import config

async def auth():
    print("🔐 Авторизация в Telegram")
    print(f"API ID: {config.TG_API_ID}")
    print(f"API Hash: {config.TG_API_HASH}")
    
    if not config.TG_API_ID or not config.TG_API_HASH:
        print("❌ Ошибка: добавьте TG_API_ID и TG_API_HASH в .env файл")
        print("📝 Инструкция: https://my.telegram.org/apps")
        return
    
    session_file = config.DATA_DIR / "telegram_session"
    client = TelegramClient(str(session_file), config.TG_API_ID, config.TG_API_HASH)
    
    await client.start()
    print("✅ Авторизация успешна!")
    print("📁 Файл сессии сохранён:", session_file)
    
    # Проверяем
    me = await client.get_me()
    print(f"👤 Авторизован как: {me.first_name} (@{me.username})")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(auth())