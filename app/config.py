import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

class Config:
    # База данных
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/news.db")
    
    # LLM
    LLM_URL = os.getenv("LLM_URL", "http://localhost:11434/api/chat")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:2b")
    LLM_TIMEOUT = 120
    
    # Admin
    ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "as612aj@$^")
    
    # Парсинг
    TG_API_ID = int(os.getenv("TG_API_ID", "0")) if os.getenv("TG_API_ID") else None
    TG_API_HASH = os.getenv("TG_API_HASH")
    
    # Пути
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    USERS_DIR = DATA_DIR / "users"
    ML_MODELS_DIR = BASE_DIR / "ml_models"
    
    # Безопасность
    MAX_LOGIN_ATTEMPTS = 5
    BLOCK_MINUTES = 15
    
config = Config()

# Создаем директории
config.DATA_DIR.mkdir(exist_ok=True)
config.USERS_DIR.mkdir(exist_ok=True)
config.ML_MODELS_DIR.mkdir(exist_ok=True)