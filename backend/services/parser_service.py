# -*- coding: utf-8 -*-
"""
ParserService — сбор новостей из Telegram-каналов и Lenta.ru (RSS).
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx
import re

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import backend.config as cfg
from database.init_db import SessionLocal
from database.models import News
from sqlalchemy import select


def _clean_html(html_text: str) -> str:
    """Удаляет HTML-теги и сущности из текста."""
    if not html_text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = re.sub(r'&[a-z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class LentaParser:
    """Парсер новостей Lenta.ru через RSS-ленту."""

    @staticmethod
    async def fetch_news() -> list[dict]:
        """Загружает и парсит RSS-ленту Lenta.ru. Возвращает список словарей новостей."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(cfg.LENTA_RSS_URL)
                resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить RSS Lenta.ru: {e}")

        if not resp.text or "<?xml" not in resp.text and "<rss" not in resp.text:
            raise RuntimeError("Lenta.ru вернула не RSS, а HTML. Возможно, изменился URL.")

        feed = feedparser.parse(resp.text)
        if not feed.entries:
            raise RuntimeError("RSS-лента Lenta.ru пуста")

        news_list = []

        for entry in feed.entries[:50]:
            subject = None
            if hasattr(entry, "tags") and entry.tags:
                subject = entry.tags[0].get("term", None)

            published = datetime.now(timezone.utc)
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            # Lenta.RSS кладёт текст в description, а summary пустой
            raw_body = (entry.get("summary") or entry.get("description") or entry.get("title") or "")
            news_body = _clean_html(raw_body)

            # Если текст слишком короткий — пробуем загрузить полную статью
            if len(news_body) < 100 and entry.get("link"):
                try:
                    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                        article_resp = await client.get(entry["link"])
                        if article_resp.status_code == 200:
                            article_html = article_resp.text
                            # Извлекаем текст статьи (Lenta использует <div class="b-text"> или <p>)
                            text_match = re.search(
                                r'<div[^>]*class="[^"]*b-text[^"]*"[^>]*>(.*?)</div>',
                                article_html, re.DOTALL
                            )
                            if text_match:
                                news_body = _clean_html(text_match.group(1))
                            else:
                                # Fallback: все <p> подряд
                                paragraphs = re.findall(
                                    r'<p[^>]*>(.*?)</p>', article_html, re.DOTALL
                                )
                                if paragraphs:
                                    news_body = _clean_html("\n".join(paragraphs))
                except Exception:
                    pass  # Оставляем то, что есть из RSS

            news_list.append({
                "published_at": published,
                "channel": "Lenta.ru",
                "news_body": news_body,
                "news_link": entry.get("link", ""),
                "subject": subject or "Новости",
                "source": "lenta",
                "views": 0,
                "forwarded": 0,
            })

        return news_list

    @staticmethod
    async def save_news(news_list: list[dict]) -> int:
        """Сохраняет новые новости в БД (пропускает дубли по ссылке). Возвращает кол-во добавленных."""
        saved = 0
        async with SessionLocal() as db:
            for item in news_list:
                # Проверка на дубликат
                stmt = select(News).where(News.news_link == item["news_link"])
                exists = (await db.execute(stmt)).scalar_one_or_none()
                if exists:
                    continue

                news = News(
                    published_at=item["published_at"],
                    channel=item["channel"],
                    news_body=item["news_body"],
                    news_link=item["news_link"],
                    subject=item["subject"],
                    news_source=item["source"],
                    views=item["views"],
                    forwarded=item["forwarded"],
                )
                db.add(news)
                saved += 1

            if saved:
                await db.commit()
        return saved


class TelegramChannelParser:
    """Парсер новостей из Telegram-каналов через Telethon."""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from telethon import TelegramClient
            session_path = str(cfg.PROJECT_ROOT / "data" / "tg_session" / "parser")
            self._client = TelegramClient(
                session_path, cfg.TG_API_ID, cfg.TG_API_HASH,
                system_version="4.16.30-vxCUSTOM"
            )
            await self._client.start()
        return self._client

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def fetch_channel_news(
        self,
        channel_username: str,
        limit: int = 200,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Загружает сообщения из одного канала.
        Если указаны date_from/date_to — запрашивает сообщения только в этом диапазоне.
        """
        client = await self._get_client()
        entity = await client.get_entity(channel_username)
        messages = []

        # Параметры для iter_messages
        kwargs = {"limit": limit}

        # Если указан date_to — начинаем с него (итерируемся назад во времени)
        if date_to:
            kwargs["offset_date"] = date_to

        async for msg in client.iter_messages(entity, **kwargs):
            if not msg.text:
                continue

            msg_date = msg.date.replace(tzinfo=timezone.utc) if msg.date else None
            if not msg_date:
                continue

            # Если мы уже вышли за нижнюю границу диапазона — стоп
            if date_from and msg_date < date_from:
                break

            # Если date_to задан, но сообщение новее его — пропускаем
            if date_to and msg_date > date_to:
                continue

            messages.append({
                "published_at": msg_date,
                "channel": channel_username.lstrip("@"),
                "news_body": msg.text,
                "news_link": f"https://t.me/{channel_username.lstrip('@')}/{msg.id}",
                "subject": "Новости",
                "source": "tg",
                "views": msg.views or 0,
                "forwarded": msg.forwards or 0,
            })

        return messages

    async def fetch_multiple_channels(
        self,
        channels: list[str],
        limit: int = 200,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[dict]:
        """Загружает новости из списка каналов последовательно (один клиент)."""
        all_news = []
        try:
            for username in channels:
                try:
                    news = await self.fetch_channel_news(username, limit, date_from, date_to)
                    all_news.extend(news)
                    print(f"  [TG] @{username}: +{len(news)} сообщений")
                except Exception as e:
                    print(f"  [TG WARN] @{username}: {e}")
        finally:
            await self.disconnect()
        return all_news

    async def save_news(self, news_list: list[dict]) -> int:
        """Сохраняет новые новости в БД (пропускает дубли по ссылке)."""
        saved = 0
        async with SessionLocal() as db:
            for item in news_list:
                stmt = select(News).where(News.news_link == item["news_link"])
                exists = (await db.execute(stmt)).scalar_one_or_none()
                if exists:
                    continue

                news = News(
                    published_at=item["published_at"],
                    channel=item["channel"],
                    news_body=item["news_body"],
                    news_link=item["news_link"],
                    subject=item["subject"],
                    news_source=item["source"],
                    views=item["views"],
                    forwarded=item["forwarded"],
                )
                db.add(news)
                saved += 1

            if saved:
                await db.commit()
        return saved
