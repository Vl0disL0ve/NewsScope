# -*- coding: utf-8 -*-
"""
TelegramBot — телеграм-бот для краткого пересказа новостей.
Использует aiogram 3.x. Поддерживает пользовательские и админские команды.
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, FSInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

import backend.config as cfg
from backend.services.auth_service import AuthService
from backend.services.news_service import NewsService
from backend.services.cluster_service import ClusterService
from backend.services.parser_service import LentaParser
from database.init_db import SessionLocal
from database.models import User, Cluster, ActionLog, EntryLog
from sqlalchemy import select, func

logger = logging.getLogger(__name__)


# ─── FSM-состояния ────────────────────────────────────────────

class AdminAddUser(StatesGroup):
    waiting_login = State()
    waiting_password = State()


class SummaryPeriod(StatesGroup):
    waiting_period = State()
    waiting_channels = State()


class AdminVisitStats(StatesGroup):
    waiting_interval = State()
    waiting_user = State()


class SearchState(StatesGroup):
    waiting_query = State()


class ChronologyState(StatesGroup):
    waiting_cluster = State()


# ─── Клавиатуры ───────────────────────────────────────────────

def main_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="📰 Последние новости", callback_data="news_latest")
    kb.button(text="🔍 Поиск", callback_data="search_start")
    kb.button(text="📊 Мои кластеры", callback_data="my_clusters")
    kb.button(text="📝 Саммари по периоду", callback_data="summary_period")
    kb.button(text="🌐 Загрузить Lenta.ru", callback_data="lenta")
    kb.adjust(2)
    if is_admin:
        kb.button(text="⚙️ Админ-панель", callback_data="admin_panel")
    return kb.as_markup()


def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Добавить пользователя", callback_data="admin_add_user")
    kb.button(text="📊 Статистика посещений", callback_data="admin_visits")
    kb.button(text="📈 Новые пользователи", callback_data="admin_new_users")
    kb.button(text="💾 Статистика БД", callback_data="admin_db")
    kb.button(text="🔙 Назад", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def interval_kb(prefix: str = "visit"):
    kb = InlineKeyboardBuilder()
    kb.button(text="За день", callback_data=f"{prefix}_day")
    kb.button(text="За неделю", callback_data=f"{prefix}_week")
    kb.button(text="За месяц", callback_data=f"{prefix}_month")
    kb.button(text="🔙 Назад", callback_data="admin_panel")
    kb.adjust(3, 1)
    return kb.as_markup()


class TelegramBot:
    """Контроллер Telegram-бота."""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._running = False
        self._storage = MemoryStorage()

    def _setup_handlers(self):
        dp = self.dp

        # ─── /start ───────────────────────────────────────
        @dp.message(CommandStart())
        async def cmd_start(message: Message, state: FSMContext):
            await state.clear()
            user = await self._get_or_create_user(message)
            is_admin = user and user.get("role") == "admin"
            await message.answer(
                f"👋 Здравствуйте, {message.from_user.full_name}!\n\n"
                "Я — бот для краткого пересказа новостей.\n"
                "Собираю новости из Telegram-каналов и Lenta.ru, "
                "группирую по темам и делаю пересказы.\n\n"
                "📋 Команды:\n"
                "/news — последние новости\n"
                "/search — поиск новостей\n"
                "/cluster — мои кластеры\n"
                "/lenta — загрузить Lenta.ru\n"
                "/recent — 10 последних новостей\n"
                "/summary — саммари за период\n"
                "/chronology — хронология по кластеру",
                reply_markup=main_kb(is_admin),
            )

        # ─── /news ────────────────────────────────────────
        @dp.message(Command("news"))
        async def cmd_news(message: Message):
            service = NewsService()
            news = await service.get_news(limit=10)
            if not news:
                await message.answer("📭 Новостей пока нет. /lenta для загрузки.")
                return
            lines = ["📰 *Последние новости:*\n"]
            for n in news:
                icon = "📱" if n["source"] == "tg" else "🌐"
                date_str = n["published_at"][:16].replace("T", " ")
                lines.append(
                    f"{icon} *{n.get('subject','Новости')[:60]}*\n"
                    f"  {n['news_body'][:120]}...\n"
                    f"  _{date_str}_\n"
                )
            await message.answer("\n".join(lines), parse_mode="Markdown",
                                 disable_web_page_preview=True)

        # ─── /search ──────────────────────────────────────
        @dp.message(Command("search"))
        async def cmd_search(message: Message, state: FSMContext):
            query = message.text.replace("/search", "", 1).strip()
            if not query:
                await state.set_state(SearchState.waiting_query)
                await message.answer("🔍 Введите поисковый запрос:")
                return
            await _do_search(message, query)

        @dp.message(SearchState.waiting_query)
        async def process_search_query(message: Message, state: FSMContext):
            await state.clear()
            await _do_search(message, message.text.strip())

        async def _do_search(message: Message, query: str):
            await message.answer(f"🔍 Ищу: «{query}»...")
            service = NewsService()
            results = await service.get_news(search_query=query, limit=10)
            if not results:
                await message.answer(f"😕 Ничего не найдено по «{query}»")
                return
            lines = [f"🔍 *Результаты:* «{query}»\n"]
            for n in results[:10]:
                date_str = n["published_at"][:16].replace("T", " ")
                lines.append(
                    f"• *{n.get('subject','?')[:60]}* {n['news_body'][:100]}...\n"
                    f"  _{date_str}_\n"
                )
            await message.answer("\n".join(lines), parse_mode="Markdown",
                                 disable_web_page_preview=True)

        # ─── /lenta ───────────────────────────────────────
        @dp.message(Command("lenta"))
        async def cmd_lenta(message: Message):
            await message.answer("⏳ Загружаю Lenta.ru...")
            try:
                parser = LentaParser()
                news = await parser.fetch_news()
                saved = await parser.save_news(news)
                await message.answer(f"✅ Загружено: {len(news)}, новых: {saved}")
            except Exception as e:
                await message.answer(f"⚠️ Ошибка: {e}")

        # ─── /cluster ─────────────────────────────────────
        @dp.message(Command("cluster"))
        async def cmd_clusters(message: Message):
            user = await self._get_or_create_user(message)
            if not user:
                await message.answer("⚠️ Не удалось определить пользователя")
                return
            service = ClusterService()
            clusters = await service.get_clusters_by_user(user["user_id"], limit=5)
            if not clusters:
                await message.answer("📊 У вас пока нет кластеров. /summary — создать.")
                return

            for c in clusters:
                has_audio = "🎤" if c.get("audio_path") else ""
                date_str = c["created_at"][:16].replace("T", " ")
                kb = InlineKeyboardBuilder()
                kb.button(text="🎧 Озвучить", callback_data=f"tts_{c['cluster_id']}")
                kb.button(text="📅 Хронология", callback_data=f"chrono_{c['cluster_id']}")
                text = (
                    f"🔹 #{c['cluster_id']} *{c.get('cluster_title',c['topic'])[:80]}* {has_audio}\n"
                    f"📰 Новостей: {c.get('news_count','?')} | {date_str}\n"
                    f"📝 {c.get('summary','')[:200]}...\n"
                    f"📡 {', '.join(c.get('news_sources',[]))}"
                )
                await message.answer(text, parse_mode="Markdown",
                                     reply_markup=kb.as_markup())

        # ─── /recent ──────────────────────────────────────
        @dp.message(Command("recent"))
        async def cmd_recent(message: Message):
            service = NewsService()
            news = await service.get_news(limit=10)
            if not news:
                await message.answer("📭 Новостей пока нет.")
                return
            lines = ["📰 *10 последних:*\n"]
            for n in news:
                date_str = n["published_at"][:16].replace("T", " ")
                lines.append(f"• [{n['source']}] {n['news_body'][:100]}... | {date_str}\n")
            await message.answer("\n".join(lines), parse_mode="Markdown",
                                 disable_web_page_preview=True)

        # ─── /summary (период) ────────────────────────────
        @dp.message(Command("summary"))
        async def cmd_summary(message: Message, state: FSMContext):
            await state.set_state(SummaryPeriod.waiting_period)
            await message.answer(
                "📅 Введите период в формате:\n"
                "`ДД.ММ.ГГГГ ЧЧ:ММ - ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
                "Например: `01.06.2026 00:00 - 09.06.2026 23:59`",
                parse_mode="Markdown",
            )

        @dp.message(SummaryPeriod.waiting_period)
        async def process_summary_period(message: Message, state: FSMContext):
            text = message.text.strip()
            parts = text.split(" - ")
            if len(parts) != 2:
                await message.answer("⚠️ Неверный формат. Пример: 01.06.2026 00:00 - 09.06.2026 23:59")
                return

            try:
                d1 = datetime.strptime(parts[0].strip(), "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
                d2 = datetime.strptime(parts[1].strip(), "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
            except ValueError:
                await message.answer("⚠️ Неверный формат даты.")
                return

            await state.update_data(date_from=d1.isoformat(), date_to=d2.isoformat())
            await state.set_state(SummaryPeriod.waiting_channels)
            await message.answer(
                "📡 Введите каналы через запятую (или `all` для всех):\n"
                "Например: `ТАСС, РБК, Lenta.ru`",
            )

        @dp.message(SummaryPeriod.waiting_channels)
        async def process_summary_channels(message: Message, state: FSMContext):
            channels_raw = message.text.strip()
            data = await state.get_data()
            await state.clear()

            user = await self._get_or_create_user(message)
            if not user:
                await message.answer("⚠️ Ошибка пользователя")
                return

            await message.answer("⏳ Запускаю кластеризацию... Это может занять пару минут.")

            try:
                channels_param = None
                if channels_raw.lower() != "all":
                    channels_param = channels_raw

                # Вызываем авто-кластеризацию через ClusterService
                news_svc = NewsService()
                news_list = await news_svc.get_news(
                    date_from=datetime.fromisoformat(data["date_from"]),
                    date_to=datetime.fromisoformat(data["date_to"]),
                    limit=500,
                )

                if len(news_list) < 2:
                    await message.answer("📭 Недостаточно новостей за период.")
                    return

                # Кластеризация через ML
                texts = [n["news_body"] for n in news_list]
                ids = [n["news_id"] for n in news_list]

                def _cluster(texts, k):
                    from ai_agent.services import SummaryService
                    svc = SummaryService()
                    emb = svc.get_embeddings(texts)
                    return svc.cluster_with_faiss(emb, k)

                k = min(5, len(texts))
                loop = asyncio.get_event_loop()
                clusters_raw = await loop.run_in_executor(None, _cluster, texts, k)

                cluster_svc = ClusterService()
                count = 0
                for label, indices in clusters_raw.items():
                    cluster_news = [ids[i] for i in indices]
                    cluster_texts = [texts[i] for i in indices if texts[i].strip()]
                    sources = list(set(n["channel"] for i in indices for n in [news_list[i]]))

                    combined = "\n\n".join(cluster_texts[:10])
                    if len(combined) >= 50:
                        try:
                            from ai_agent.services import SummaryService as SS
                            llm = SS(load_embeddings=False, llm_url=cfg.LLM_URL, llm_model=cfg.LLM_MODEL)
                            title, summary = await llm.summarize_with_llm(combined)
                        except Exception:
                            title = "Новости"
                            summary = f"Кластер из {len(cluster_news)} новостей."
                    else:
                        title = "Новости"
                        summary = f"Кластер из {len(cluster_news)} новостей."

                    await cluster_svc.create_cluster(
                        user_id=user["user_id"],
                        topic=cluster_texts[0][:80] if cluster_texts else "Новости",
                        cluster_title=title,
                        summary=summary,
                        news_ids=cluster_news,
                        news_sources=sources,
                    )
                    count += 1

                await message.answer(
                    f"✅ Кластеризация завершена!\n"
                    f"Создано кластеров: {count}\n"
                    f"Новостей: {len(news_list)}\n"
                    f"Период: {data['date_from'][:10]} — {data['date_to'][:10]}\n\n"
                    f"Используйте /cluster для просмотра."
                )
            except Exception as e:
                await message.answer(f"⚠️ Ошибка кластеризации: {e}")

        # ─── /chronology ──────────────────────────────────
        @dp.message(Command("chronology"))
        async def cmd_chronology(message: Message, state: FSMContext):
            user = await self._get_or_create_user(message)
            if not user:
                await message.answer("⚠️ Ошибка.")
                return
            service = ClusterService()
            clusters = await service.get_clusters_by_user(user["user_id"], limit=10)
            if not clusters:
                await message.answer("📊 Нет кластеров. /summary — создать.")
                return

            await state.set_state(ChronologyState.waiting_cluster)
            kb = InlineKeyboardBuilder()
            for c in clusters:
                title = (c.get("cluster_title") or c["topic"])[:40]
                kb.button(text=f"#{c['cluster_id']} {title}", callback_data=f"chrono_{c['cluster_id']}")
            kb.adjust(1)
            await message.answer("📅 Выберите кластер для хронологии:", reply_markup=kb.as_markup())

        @dp.message(ChronologyState.waiting_cluster)
        async def process_chronology_cluster(message: Message, state: FSMContext):
            await state.clear()
            await message.answer("Используйте /chronology и выберите кластер из списка.")

        # ─── Callback-обработчики ──────────────────────────
        @dp.callback_query()
        async def handle_callback(callback: CallbackQuery, state: FSMContext):
            data = callback.data
            user = await self._get_or_create_user(callback.message)
            if not user:
                await callback.answer("⚠️ Ошибка")
                return

            # ─── Основные кнопки ──────────────────────
            if data == "news_latest":
                await cmd_news(callback.message)
            elif data == "search_start":
                await state.set_state(SearchState.waiting_query)
                await callback.message.answer("🔍 Введите поисковый запрос:")
            elif data == "my_clusters":
                await cmd_clusters(callback.message)
            elif data == "lenta":
                await cmd_lenta(callback.message)
            elif data == "summary_period":
                await cmd_summary(callback.message, state)
            elif data == "back_main":
                is_admin = user.get("role") == "admin"
                await callback.message.answer("🏠 Главное меню:", reply_markup=main_kb(is_admin))

            # ─── TTS ─────────────────────────────────
            elif data.startswith("tts_"):
                cluster_id = int(data.split("_")[1])
                await callback.answer("⏳ Генерирую аудио...")
                try:
                    svc = ClusterService()
                    cluster = await svc.get_cluster_detail(cluster_id)
                    if not cluster or not cluster.get("summary"):
                        await callback.message.answer("⚠️ Сначала создайте саммари.")
                        return

                    from ai_agent.services import TTSService
                    tts = TTSService()
                    audio_path = await tts.text_to_speech(
                        cluster["summary"], cluster_id,
                        str(_project_root / "data" / user["login"]),
                    )
                    await svc.set_audio_path(cluster_id, audio_path)

                    voice_file = FSInputFile(audio_path)
                    await callback.message.answer_voice(
                        voice_file,
                        caption=f"🎧 Пересказ: {cluster.get('cluster_title', cluster['topic'])[:100]}",
                    )
                except Exception as e:
                    await callback.message.answer(f"⚠️ Ошибка TTS: {e}")

            # ─── Хронология ──────────────────────────
            elif data.startswith("chrono_"):
                cluster_id = int(data.split("_")[1])
                await callback.answer("⏳ Строю хронологию...")
                try:
                    svc = ClusterService()
                    result = await svc.build_chronology(cluster_id, user["login"])
                    if result.get("success"):
                        text = result["chronology"][:4000]
                        await callback.message.answer(
                            f"📅 *Хронология (кластер #{cluster_id})*\n\n{text}",
                            parse_mode="Markdown",
                        )
                    else:
                        await callback.message.answer(f"⚠️ {result.get('error','?')}")
                except Exception as e:
                    await callback.message.answer(f"⚠️ Ошибка: {e}")

            # ─── Админ-панель ────────────────────────
            elif data == "admin_panel":
                if user.get("role") != "admin":
                    await callback.answer("⛔ Нет доступа")
                    return
                await callback.message.answer("⚙️ Админ-панель:", reply_markup=admin_kb())

            # ─── Добавить пользователя ───────────────
            elif data == "admin_add_user":
                if user.get("role") != "admin":
                    await callback.answer("⛔ Нет доступа")
                    return
                await state.set_state(AdminAddUser.waiting_login)
                await callback.message.answer("👤 Введите *Логин* нового пользователя:", parse_mode="Markdown")

            # ─── Статистика посещений ────────────────
            elif data == "admin_visits":
                if user.get("role") != "admin":
                    await callback.answer("⛔ Нет доступа")
                    return
                await callback.message.answer("📊 Выберите интервал:", reply_markup=interval_kb("visit"))

            elif data.startswith("visit_"):
                interval = data.split("_")[1]
                await callback.answer("⏳ Загрузка...")
                try:
                    resp_data = await self._get_stats("visits", interval)
                    text = self._format_stats(resp_data, "Посещения")
                    await callback.message.answer(text, parse_mode="Markdown")
                except Exception as e:
                    await callback.message.answer(f"⚠️ {e}")

            # ─── Новые пользователи ──────────────────
            elif data == "admin_new_users":
                if user.get("role") != "admin":
                    await callback.answer("⛔ Нет доступа")
                    return
                await callback.message.answer("📈 Выберите интервал:", reply_markup=interval_kb("newu"))

            elif data.startswith("newu_"):
                interval = data.split("_")[1]
                await callback.answer("⏳ Загрузка...")
                try:
                    resp_data = await self._get_stats("users", interval)
                    text = self._format_stats(resp_data, "Новые пользователи")
                    await callback.message.answer(text, parse_mode="Markdown")
                except Exception as e:
                    await callback.message.answer(f"⚠️ {e}")

            # ─── Статистика БД ───────────────────────
            elif data == "admin_db":
                if user.get("role") != "admin":
                    await callback.answer("⛔ Нет доступа")
                    return
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            f"http://localhost:{cfg.PORT}/api/admin/stats/database",
                            headers={"Authorization": f"Bearer {await self._make_token(user)}"},
                        )
                        db_data = resp.json()
                    text = (
                        f"💾 *Статистика БД*\n\n"
                        f"👥 Пользователей: {db_data.get('users',0)}\n"
                        f"📰 Новостей: {db_data.get('news',0)}\n"
                        f"📊 Кластеров: {db_data.get('clusters',0)}\n"
                        f"📝 Действий: {db_data.get('actions',0)}\n"
                        f"💿 Данные: {db_data.get('user_data_mb',0)} МБ\n"
                        f"🗄️ Диск: {db_data.get('disk_free_gb',0)} ГБ свободно из {db_data.get('disk_total_gb',0)} ГБ"
                    )
                    await callback.message.answer(text, parse_mode="Markdown")
                except Exception as e:
                    await callback.message.answer(f"⚠️ {e}")

            await callback.answer()

        # ─── FSM: добавление пользователя ──────────────────
        @dp.message(AdminAddUser.waiting_login)
        async def process_admin_login(message: Message, state: FSMContext):
            login = message.text.strip()
            if len(login) < 3:
                await message.answer("⚠️ Логин должен быть не менее 3 символов.")
                return
            await state.update_data(new_user_login=login)
            await state.set_state(AdminAddUser.waiting_password)
            await message.answer("🔑 Введите *Пароль*:", parse_mode="Markdown")

        @dp.message(AdminAddUser.waiting_password)
        async def process_admin_password(message: Message, state: FSMContext):
            password = message.text.strip()
            if len(password) < 4:
                await message.answer("⚠️ Пароль должен быть не менее 4 символов.")
                return
            data = await state.get_data()
            login = data["new_user_login"]
            await state.clear()

            auth = AuthService()
            result = await auth.register(login=login, password=password)
            if result["success"]:
                await message.answer(f"✅ Пользователь *{login}* добавлен!", parse_mode="Markdown")
            else:
                await message.answer(f"⚠️ {result.get('error','Ошибка')}")

        # ─── Неизвестные команды ─────────────────────────
        @dp.message()
        async def handle_unknown(message: Message, state: FSMContext):
            text = (message.text or "").strip()
            if text and not text.startswith("/"):
                service = NewsService()
                results = await service.get_news(search_query=text, limit=5)
                if results:
                    lines = [f"🔍 *По запросу:* «{text}»\n"]
                    for n in results:
                        lines.append(f"• {n['news_body'][:100]}...\n")
                    await message.answer("\n".join(lines), parse_mode="Markdown",
                                         disable_web_page_preview=True)
                else:
                    await message.answer("🤖 Используйте /help или меню.")
            else:
                await message.answer("🤖 Используйте /start для меню.")

    # ─── Вспомогательные методы ───────────────────────────────

    async def _get_or_create_user(self, message: Message) -> Optional[dict]:
        tg_id = str(message.from_user.id)
        auth = AuthService()

        async with SessionLocal() as db:
            stmt = select(User).where(User.tg_uuid == tg_id)
            user = (await db.execute(stmt)).scalar_one_or_none()

        if user:
            result = await auth.login_by_tg(tg_uuid=tg_id)
            if result["success"]:
                return await auth.get_current_user(result["token"])

        login = f"tg_{message.from_user.username or tg_id}"
        reg = await auth.register(login=login, password=tg_id, tg_uuid=tg_id)
        if reg["success"]:
            return await auth.get_current_user(reg["token"])
        return None

    async def _make_token(self, user: dict) -> str:
        auth = AuthService()
        result = await auth.login_by_tg(tg_uuid=user.get("tg_uuid", ""))
        if result["success"]:
            return result["token"]
        return ""

    async def _get_stats(self, kind: str, interval: str) -> list:
        import httpx
        async with httpx.AsyncClient() as client:
            # Используем внутренний вызов — напрямую через сервис
            from backend.controllers.admin_controller import visit_stats, user_stats
            if kind == "visits":
                return await visit_stats(interval=interval, current_user={"role": "admin"})
            else:
                return await user_stats(interval=interval, current_user={"role": "admin"})

    @staticmethod
    def _format_stats(data: list, title: str) -> str:
        if not data:
            return f"📊 *{title}*: нет данных"
        total = sum(r.get("value", 0) for r in data)
        lines = [f"📊 *{title}*\nВсего: {total}\n"]
        for r in data[:20]:
            lines.append(f"  {r['label']}: {r['value']}")
        return "\n".join(lines)

    # ─── Запуск / остановка ──────────────────────────────────

    async def start(self):
        if not cfg.TG_BOT_TOKEN:
            logger.warning("⚠️ TG_BOT_TOKEN не указан, бот не запущен")
            return

        self.bot = Bot(token=cfg.TG_BOT_TOKEN)
        self.dp = Dispatcher(storage=self._storage)
        self._setup_handlers()
        self._running = True

        logger.info("🤖 Telegram-бот запущен")
        try:
            await self.dp.start_polling(self.bot)
        finally:
            await self.bot.session.close()

    def stop(self):
        self._running = False


# ─── Запуск из командной строки ─────────────────────────────────
if __name__ == "__main__":
    import asyncio
    bot = TelegramBot()
    asyncio.run(bot.start())
