# -*- coding: utf-8 -*-
"""
Конфигурация приложения.
Загружает переменные из .env с валидацией типов.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Явный путь к .env (не зависит от CWD) + override (перезаписывает stale env)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

# ─── Корень проекта ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── База данных ───
DATABASE_URL: str = (
    os.getenv("DATABASE_URL")
    or os.getenv("DB_URL")
    or "postgresql+asyncpg://postgres:postgres@localhost:5432/digest_ai"
)

# ─── JWT / Сессии ───
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
SESSION_EXPIRE_HOURS: int = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))

# ─── Сервер ───
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")

# ─── ML (Ollama) ───
LLM_URL: str = os.getenv("LLM_URL", "http://localhost:11434/api/chat")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemma4:12b")

# ─── Telegram ───
TG_BOT_TOKEN: str | None = os.getenv("TG_BOT_TOKEN")
TG_API_ID: int | None = int(os.getenv("TG_API_ID", "0")) or None
TG_API_HASH: str | None = os.getenv("TG_API_HASH")

# ─── Парсеры ───
LENTA_RSS_URL: str = "https://lenta.ru/rss/news"
PARSER_INTERVAL_MINUTES: int = int(os.getenv("PARSER_INTERVAL_MINUTES", "15"))

# ─── Пути ───
FRONTEND_DIR: Path = PROJECT_ROOT / "frontend"
ML_MODELS_DIR: Path = PROJECT_ROOT / "ml_models"
