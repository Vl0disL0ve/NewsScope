# -*- coding: utf-8 -*-
"""
Точка входа для запуска Telegram-бота (standalone).
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import asyncio
import os
from dotenv import load_dotenv
from backend.bot.telegram_bot import TelegramBot

load_dotenv()

async def main():
    bot = TelegramBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
