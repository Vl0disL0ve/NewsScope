from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio

from app.api.web import router as web_router
from app.services.scheduler import scheduler

app = FastAPI(title="News Aggregator API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Подключаем API роутеры
app.include_router(web_router)

# Простая загрузка HTML
def get_html(filename: str) -> HTMLResponse:
    file_path = templates_dir / filename
    if file_path.exists():
        return HTMLResponse(content=file_path.read_text(encoding='utf-8'))
    return HTMLResponse(content=f"<h1>404 - {filename}</h1>", status_code=404)

# WEB страницы
@app.get("/")
async def root():
    return RedirectResponse(url="/login")

@app.get("/login")
@app.get("/login/")
@app.get("/login/login.html")
async def login_page():
    return get_html("login.html")

@app.get("/main")
@app.get("/main/")
@app.get("/main/main.html")
async def main_page():
    return get_html("main.html")

@app.get("/history")
@app.get("/history/")
@app.get("/history/history.html")
async def history_page():
    return get_html("history.html")

@app.get("/admin")
@app.get("/admin/")
@app.get("/admin/admin.html")
async def admin_page():
    return get_html("admin.html")

@app.on_event("startup")
async def startup_event():
    """Запуск фонового парсера при старте сервера"""
    print("🚀 Запуск сервера...")
    # Запускаем шедулер в отдельном потоке, чтобы не блокировать asyncio
    import threading
    thread = threading.Thread(target=scheduler.start, daemon=True)
    thread.start()
    print("✅ Фоновый парсер запущен (каждые 1 час)")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Остановка сервера...")
    scheduler.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)