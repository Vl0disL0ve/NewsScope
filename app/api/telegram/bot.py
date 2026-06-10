import asyncio
import logging
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import config
from app.database.session import AsyncSessionLocal
from app.database.crud import UserCRUD, SettingsCRUD, ClusterCRUD, HistoryCRUD, NewsCRUD
from app.services.auth_service import AuthService
from app.services.parser_service import ParserService
from app.services.cluster_service import ClusterService
from app.services.tts_service import TTSService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummaryState(StatesGroup):
    waiting_period = State()
    waiting_channels = State()

class SearchState(StatesGroup):
    waiting_query = State()

bot = Bot(token=config.BOT_TOKEN) if config.BOT_TOKEN else None
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_user_token(user_id: int, login: str) -> str:
    return f"user_{user_id}_{login}"

async def get_current_user(tg_id: int):
    async with AsyncSessionLocal() as db:
        user_crud = UserCRUD(db)
        return await user_crud.get_by_tg_id(tg_id)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    username = message.from_user.username or f"user_{tg_id}"
    
    async with AsyncSessionLocal() as db:
        user_crud = UserCRUD(db)
        user = await user_crud.get_by_tg_id(tg_id)
        
        if not user:
            auth_service = AuthService(db)
            password_hash = auth_service.hash_password(str(tg_id))
            user = await user_crud.create(
                login=username,
                password_hash=password_hash,
                role="user",
                tg_id=tg_id
            )
            await message.answer(f"✅ Вы зарегистрированы! Ваш логин: {username}")
        else:
            await message.answer(f"👋 С возвращением, {user.login}!")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📰 Парсинг новостей", callback_data="parse_all")],
        [InlineKeyboardButton(text="📊 Кластеризация", callback_data="cluster_run")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_start")],
        [InlineKeyboardButton(text="🎧 Мои аудио", callback_data="my_audio")]
    ])
    
    await message.answer(
        "🤖 Бот для анализа новостей\n\n"
        "Что хотите сделать?",
        reply_markup=kb
    )

@dp.callback_query(F.data == "parse_all")
async def parse_all_callback(callback: types.CallbackQuery):
    await callback.answer("Начинаю парсинг...")
    await callback.message.edit_text("⏳ Парсинг Lenta.ru и Telegram каналов...")
    
    parser = ParserService()
    lenta_news = await parser.parse_lenta(30)
    tg_news = await parser.parse_telegram(["rian_ru", "rt_russian", "kommersant"], 20)
    await parser.close()
    
    total = len(lenta_news) + len(tg_news)
    await callback.message.edit_text(
        f"✅ Парсинг завершён!\n"
        f"📰 Lenta.ru: {len(lenta_news)} новостей\n"
        f"📱 Telegram: {len(tg_news)} новостей\n"
        f"📊 Всего: {total} новостей"
    )

@dp.callback_query(F.data == "cluster_run")
async def cluster_run_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    user = await get_current_user(tg_id)
    
    if not user:
        await callback.message.answer("❌ Ошибка: пользователь не найден")
        return
    
    await callback.answer("Запускаю кластеризацию...")
    await callback.message.edit_text("⏳ Парсинг новостей и кластеризация...")
    
    # Сначала парсим новости
    parser = ParserService()
    await parser.parse_lenta(30)
    await parser.parse_telegram(["rian_ru", "rt_russian", "kommersant"], 20)
    await parser.close()
    
    # Затем кластеризация
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    cluster_service = ClusterService()
    result = await cluster_service.run_clustering(
        user_id=user.id,
        num_clusters=5,
        channels=["Lenta.ru", "rian_ru", "rt_russian", "kommersant"],
        start_date=start_date,
        end_date=end_date
    )
    
    if result.get("success"):
        clusters = result.get("clusters", [])
        text = f"✅ Кластеризация завершена!\n"
        text += f"📊 Всего новостей: {result.get('total_news', 0)}\n"
        text += f"📁 Создано кластеров: {len(clusters)}\n\n"
        
        for i, c in enumerate(clusters[:5]):
            text += f"{i+1}. {c['topic'][:60]}\n"
        
        await callback.message.edit_text(text)
    else:
        await callback.message.edit_text(f"❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}")

@dp.callback_query(F.data == "search_start")
async def search_start_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await callback.message.answer("🔍 Введите поисковый запрос:")

@dp.message(SearchState.waiting_query)
async def process_search(message: types.Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    
    await message.answer(f"🔍 Ищу: {query}...")
    
    async with AsyncSessionLocal() as db:
        news_crud = NewsCRUD(db)
        all_news = await news_crud.get_news_for_period(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            channels=[]
        )
        
        results = []
        for news in all_news:
            if query.lower() in news.news_body.lower():
                results.append(news)
        
        if results:
            text = f"📰 Найдено {len(results)} результатов:\n\n"
            for r in results[:10]:
                text += f"• {r.news_body[:100]}...\n"
            await message.answer(text)
        else:
            await message.answer("😕 Ничего не найдено")

@dp.callback_query(F.data == "my_audio")
async def my_audio_callback(callback: types.CallbackQuery):
    tg_id = callback.from_user.id
    user = await get_current_user(tg_id)
    
    if not user:
        await callback.message.answer("❌ Ошибка")
        return
    
    async with AsyncSessionLocal() as db:
        cluster_crud = ClusterCRUD(db)
        clusters = await cluster_crud.get_user_clusters(user.id)
        
        clusters_with_audio = [c for c in clusters if c.audio_path]
        
        if not clusters_with_audio:
            await callback.message.answer("🎧 У вас пока нет сгенерированных аудио")
            return
        
        text = "🎧 Ваши аудиофайлы:\n\n"
        for c in clusters_with_audio[:10]:
            text += f"• Кластер #{c.id}: {c.topic[:50]}\n"
        
        await callback.message.answer(text)

async def main():
    if not bot:
        logger.error("BOT_TOKEN не настроен в .env")
        return
    
    logger.info("Запуск Telegram бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())