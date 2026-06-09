# -*- coding: utf-8 -*-
"""
Точка входа FastAPI-приложения.
Подключает все роутеры, статику и middleware.
"""

import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import backend.config as cfg
from backend.controllers.auth_controller import router as auth_router
from backend.controllers.news_controller import router as news_router
from backend.controllers.cluster_controller import router as cluster_router
from backend.controllers.admin_controller import router as admin_router
from backend.controllers.seed_controller import router as seed_router
from backend.controllers.parser_controller import router as parser_router


# MIME-типы по расширениям
MIME_TYPES = {
    '.js':   'application/javascript',
    '.css':  'text/css',
    '.html': 'text/html',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif':  'image/gif',
    '.svg':  'image/svg+xml',
    '.ico':  'image/x-icon',
    '.json': 'application/json',
    '.txt':  'text/plain',
    '.mp3':  'audio/mpeg',
    '.woff2':'font/woff2',
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Действия при старте и остановке приложения."""
    print(f"[Digest AI v1.0] Запуск на {cfg.HOST}:{cfg.PORT}")
    print(f"[DB] {cfg.DATABASE_URL[:50]}...")

    from database.init_db import init_db, test_connection, engine

    db_ok = await test_connection(engine)
    if not db_ok:
        print("[WARN] Не удалось подключиться к БД.")
    try:
        await init_db()
        print("[OK] Таблицы созданы/проверены")

        # Авто-seed тестовых пользователей при первом запуске
        from database.seed import seed as run_seed
        await run_seed()
    except Exception as e:
        print(f"[WARN] Ошибка инициализации: {e}")

    # Создаём необходимые директории
    root = Path(__file__).resolve().parent.parent
    (root / "data" / "audio").mkdir(parents=True, exist_ok=True)
    (root / "data" / "tg_session").mkdir(parents=True, exist_ok=True)

    # Исправляем триггер actions_check (в дампе БД INSERT без указания колонок)
    try:
        from database.init_db import engine
        async with engine.connect() as conn:
            await conn.execute(text("""
                CREATE OR REPLACE FUNCTION public.actions_check() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.audio_path IS NOT NULL THEN
                        INSERT INTO actions_log (cluster_id, action_time, action_type)
                        VALUES (NEW.cluster_id, now(), 'tts');
                    END IF;
                    IF NEW.plot_path IS NOT NULL THEN
                        INSERT INTO actions_log (cluster_id, action_time, action_type)
                        VALUES (NEW.cluster_id, now(), 'plot');
                    END IF;
                    IF NEW.chronology_path IS NOT NULL THEN
                        INSERT INTO actions_log (cluster_id, action_time, action_type)
                        VALUES (NEW.cluster_id, now(), 'chronology');
                    END IF;
                    RETURN NULL;
                END;
                $$;
            """))
            await conn.commit()
            # Добавляем колонку cluster_title, если её нет
            await conn.execute(text(
                "ALTER TABLE clusters ADD COLUMN IF NOT EXISTS cluster_title TEXT"
            ))
            await conn.commit()
            print("[OK] Триггер actions_check исправлен")
    except Exception as e:
        print(f"[WARN] Не удалось исправить триггер: {e}")

    yield
    print("[STOP] Сервер остановлен")


app = FastAPI(
    title="Digest AI — краткий пересказ новостей",
    description=(
        "API для сбора новостей из Telegram-каналов и Lenta.ru, "
        "кластеризации, краткого пересказа через LLM и TTS."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API-роутеры ────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(news_router)
app.include_router(cluster_router)
app.include_router(admin_router)
app.include_router(parser_router)
app.include_router(seed_router)


# ─── Аудио-эндпоинт (ДО serve_static, чтобы /api/audio/ не ушёл в статику) ──
@app.get("/api/audio/{cluster_id}")
async def serve_audio(cluster_id: int):
    """Отдаёт MP3-файл для плеера."""
    from backend.services.cluster_service import ClusterService
    svc = ClusterService()
    cluster = await svc.get_cluster_detail(cluster_id)
    if not cluster or not cluster.get("audio_path"):
        return JSONResponse(status_code=404, content={"detail": "Аудио не найдено"})
    audio_path = cluster["audio_path"]
    if not Path(audio_path).is_file():
        return JSONResponse(status_code=404, content={"detail": "Файл не найден"})
    return FileResponse(audio_path, media_type="audio/mpeg")


# ─── Раздача статики (frontend) ─────────────────────────────
# Единый catch-all роут для всех GET-запросов, не попавших в API.
# Не поддерживает условные запросы (304), поэтому браузер
# всегда получает свежие файлы.

@app.api_route("/{path:path}", methods=["GET"])
async def serve_static(request: Request, path: str):
    frontend = cfg.FRONTEND_DIR

    # Не трогаем API-пути
    if path.startswith("api/") or path == "api":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # 1) Точное совпадение с файлом
    file_path = frontend / path
    if file_path.is_file():
        suffix = file_path.suffix.lower()
        # Принудительно выставляем MIME для JS/CSS/HTML
        if suffix == '.js':
            media_type = 'application/javascript'
        elif suffix == '.css':
            media_type = 'text/css'
        elif suffix == '.html':
            media_type = 'text/html'
        else:
            media_type = MIME_TYPES.get(suffix, None)
        return FileResponse(str(file_path), media_type=media_type,
                            headers={"Cache-Control": "no-cache"})

    # 2) Путь без расширения — подбор вариантов
    if path and not Path(path).suffix:
        # {dir}/{dir}.html, например main/main.html
        alt = frontend / path / f"{Path(path).name}.html"
        if alt.is_file():
            return FileResponse(str(alt), media_type="text/html",
                                headers={"Cache-Control": "no-cache"})
        # {dir}/index.html
        idx = frontend / path / "index.html"
        if idx.is_file():
            return FileResponse(str(idx), media_type="text/html",
                                headers={"Cache-Control": "no-cache"})

    # 3) Корень / — index.html
    if not path:
        idx = frontend / "index.html"
        if idx.is_file():
            return FileResponse(str(idx), media_type="text/html",
                                headers={"Cache-Control": "no-cache"})

    # 4) Фолбек на страницу входа
    login = frontend / "login" / "login.html"
    if login.is_file():
        return FileResponse(str(login), media_type="text/html",
                            headers={"Cache-Control": "no-cache"})

    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# ─── Health-check ─────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
