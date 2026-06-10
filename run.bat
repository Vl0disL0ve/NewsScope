@echo off
chcp 65001 > nul
title NewsScope - Анализатор новостей

echo ========================================
echo    NewsScope - Запуск проекта
echo ========================================
echo.

:: Проверка наличия .env
if not exist .env (
    echo [WARN] Файл .env не найден, создаю базовый...
    echo LLM_URL=http://localhost:11434/api/chat > .env
    echo LLM_MODEL=gemma2:2b >> .env
    echo ADMIN_LOGIN=admin >> .env
    echo ADMIN_PASSWORD=As612aj$ >> .env
    echo DATABASE_URL=sqlite+aiosqlite:///./data/news.db >> .env
    echo TG_API_ID= >> .env
    echo TG_API_HASH= >> .env
    echo BOT_TOKEN= >> .env
    echo PARSING_INTERVAL_MINUTES=60 >> .env
    echo.
)

:: Создание папок
if not exist data mkdir data
if not exist data\users mkdir data\users
if not exist ml_models mkdir ml_models

:: Активация виртуального окружения (если есть)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Виртуальное окружение активировано
)

:: Установка зависимостей (если нужно)
echo.
echo [1/3] Проверка зависимостей...
pip install -q fastapi uvicorn sqlalchemy aiosqlite werkzeug python-dotenv beautifulsoup4 requests aiohttp telethon sentence-transformers scikit-learn edge-tts aiogram 2>nul
echo [OK] Зависимости установлены

:: Инициализация БД (если нет)
echo.
echo [2/3] Инициализация базы данных...
if not exist data\news.db (
    python -m app.database.init_db
) else (
    echo [OK] База данных уже существует
)

:: Запуск серверов
echo.
echo [3/3] Запуск серверов...
echo.
echo ========================================
echo    Сервер FastAPI: http://localhost:8000
echo    Telegram бот: запускается отдельно
echo ========================================
echo.
echo Нажмите Ctrl+C для остановки всех серверов
echo.

:: Запуск API сервера и бота в одном окне через отдельные процессы
start "NewsScope API" cmd /c "python -m app.main"
timeout /t 2 /nobreak > nul
start "NewsScope Bot" cmd /c "python -m app.bot"

echo.
echo [OK] Оба сервера запущены
echo.
echo API документация: http://localhost:8000/docs
echo.
pause