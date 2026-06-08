import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

try:
    from .models import Base
except ImportError:
    from database.models import Base


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        print("Tables:", ", ".join(table_names))


async def get_db():
    async with SessionLocal() as db:
        yield db


async def test_connection(engine: AsyncEngine) -> bool:
    """Проверка подключения к БД"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar_one()
            print(f"Connected to PostgreSQL: {version[:50]}...")
            return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False
