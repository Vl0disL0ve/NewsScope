# -*- coding: utf-8 -*-
"""
ClusterService — бизнес-логика создания и управления кластерами новостей.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from database.init_db import SessionLocal
from database.models import Cluster, News, NewsCluster, ActionLog
from sqlalchemy import select
from sqlalchemy.orm import joinedload


class ClusterService:
    """Сервис для работы с кластерами новостей."""

    @staticmethod
    async def find_cluster_by_news(news_ids: set) -> Optional[dict]:
        """Ищет кластер с точно таким же набором news_ids."""
        from database.models import NewsCluster
        async with SessionLocal() as db:
            # Находим все cluster_id, где совпадает количество новостей
            from sqlalchemy import func
            stmt = (
                select(NewsCluster.cluster_id)
                .group_by(NewsCluster.cluster_id)
                .having(func.count(NewsCluster.news_id) == len(news_ids))
            )
            result = await db.execute(stmt)
            candidate_ids = [row[0] for row in result]

            for cid in candidate_ids:
                existing = await db.execute(
                    select(NewsCluster.news_id).where(NewsCluster.cluster_id == cid)
                )
                existing_ids = {row[0] for row in existing}
                if existing_ids == news_ids:
                    # Нашли — возвращаем данные кластера
                    cluster = await db.get(Cluster, cid)
                    if cluster:
                        return {
                            "cluster_id": cluster.cluster_id,
                            "topic": cluster.topic,
                            "cluster_title": cluster.cluster_title or cluster.topic,
                            "summary": cluster.summary,
                            "news_sources": cluster.news_sources,
                            "news_count": len(news_ids),
                            "audio_path": cluster.audio_path,
                            "plot_path": cluster.plot_path,
                            "chronology_path": cluster.chronology_path,
                            "created_at": cluster.created_at.isoformat(),
                        }
            return None

    async def create_cluster(
        self,
        user_id: int,
        topic: str,
        summary: str,
        news_ids: list[int],
        news_sources: list[str],
        cluster_title: str = "",
    ) -> dict:
        """Создаёт новый кластер и привязывает к нему новости.
        Если кластер с таким же набором новостей уже существует — возвращает его."""
        # Проверяем дубликат
        existing = await self.find_cluster_by_news(set(news_ids))
        if existing:
            return existing

        async with SessionLocal() as db:
            cluster = Cluster(
                user_id=user_id,
                topic=topic,
                cluster_title=cluster_title,
                summary=summary,
                news_sources=news_sources,
            )
            db.add(cluster)
            await db.flush()

            # Привязываем новости через прямую вставку (чтобы избежать lazy load)
            from database.models import NewsCluster
            for nid in news_ids:
                news_item = await db.get(News, nid)
                if news_item:
                    db.add(NewsCluster(cluster_id=cluster.cluster_id, news_id=nid))

            await db.commit()
            await db.refresh(cluster)

            return {
                "cluster_id": cluster.cluster_id,
                "topic": cluster.topic,
                "cluster_title": cluster.cluster_title or cluster.topic,
                "summary": cluster.summary,
                "news_sources": cluster.news_sources,
                "news_count": len(news_ids),
                "created_at": cluster.created_at.isoformat(),
            }

    @staticmethod
    async def get_clusters_by_user(
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Возвращает кластеры пользователя."""
        async with SessionLocal() as db:
            stmt = (
                select(Cluster)
                .where(Cluster.user_id == user_id)
                .order_by(Cluster.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            clusters = (await db.execute(stmt)).scalars().all()

            result = []
            for c in clusters:
                actions = await db.execute(
                    select(ActionLog).where(ActionLog.cluster_id == c.cluster_id)
                )
                action_types = [a.action_type for a in actions.scalars().all()]

                # Даты новостей в кластере
                news_in_cluster = await db.execute(
                    select(News).join(NewsCluster).where(NewsCluster.cluster_id == c.cluster_id)
                )
                news_items = news_in_cluster.scalars().all()
                dates = sorted([n.published_at for n in news_items]) if news_items else []
                date_from = dates[0].strftime("%Y-%m-%d") if dates else ""
                date_to = dates[-1].strftime("%Y-%m-%d") if dates else ""

                result.append({
                    "cluster_id": c.cluster_id,
                    "topic": c.topic,
                    "cluster_title": c.cluster_title or c.topic,
                    "summary": c.summary,
                    "news_sources": c.news_sources,
                    "created_at": c.created_at.isoformat(),
                    "date_from": date_from,
                    "date_to": date_to,
                    "news_count": len(news_items),
                    "audio_path": c.audio_path,
                    "plot_path": c.plot_path,
                    "chronology_path": c.chronology_path,
                    "available_actions": action_types,
                })

            return result

    @staticmethod
    async def get_cluster_detail(cluster_id: int) -> Optional[dict]:
        """Возвращает детальную информацию о кластере с новостями."""
        async with SessionLocal() as db:
            stmt = (
                select(Cluster)
                .options(joinedload(Cluster.news_items))
                .where(Cluster.cluster_id == cluster_id)
            )
            cluster = (await db.execute(stmt)).unique().scalar_one_or_none()

            if not cluster:
                return None

            actions = await db.execute(
                select(ActionLog).where(ActionLog.cluster_id == cluster_id)
            )

            return {
                "cluster_id": cluster.cluster_id,
                "user_id": cluster.user_id,
                "topic": cluster.topic,
                "summary": cluster.summary,
                "news_sources": cluster.news_sources,
                "created_at": cluster.created_at.isoformat(),
                "audio_path": cluster.audio_path,
                "plot_path": cluster.plot_path,
                "chronology_path": cluster.chronology_path,
                "actions": [
                    {"type": a.action_type, "time": a.action_time.isoformat()}
                    for a in actions.scalars().all()
                ],
                "news_items": [
                    {
                        "news_id": n.news_id,
                        "published_at": n.published_at.isoformat(),
                        "channel": n.channel,
                        "news_body": n.news_body,
                        "news_link": n.news_link,
                        "subject": n.subject,
                        "source": n.news_source,
                    }
                    for n in cluster.news_items
                ],
            }

    @staticmethod
    async def update_cluster_summary(cluster_id: int, summary: str) -> bool:
        """Обновляет суммаризацию кластера."""
        async with SessionLocal() as db:
            cluster = await db.get(Cluster, cluster_id)
            if not cluster:
                return False
            cluster.summary = summary
            await db.commit()
            return True

    @staticmethod
    async def set_audio_path(cluster_id: int, path: str) -> bool:
        """Устанавливает путь к аудиофайлу. Триггер БД создаст запись в actions_log."""
        async with SessionLocal() as db:
            cluster = await db.get(Cluster, cluster_id)
            if not cluster:
                return False
            cluster.audio_path = path
            await db.commit()
            return True

    @staticmethod
    async def set_plot_path(cluster_id: int, path: str) -> bool:
        """Устанавливает путь к графику."""
        async with SessionLocal() as db:
            cluster = await db.get(Cluster, cluster_id)
            if not cluster:
                return False
            cluster.plot_path = path
            await db.commit()
            return True

    @staticmethod
    async def set_chronology_path(cluster_id: int, path: str) -> bool:
        """Устанавливает путь к хронологии."""
        async with SessionLocal() as db:
            cluster = await db.get(Cluster, cluster_id)
            if not cluster:
                return False
            cluster.chronology_path = path
            await db.commit()
            return True

    @staticmethod
    async def log_search_action(user_id: int, cluster_id: int, query: str) -> None:
        """
        Логирование поиска в actions_log.
        Триггер tg_actions_check отслеживает только tts/plot/chronology,
        поэтому поиск логируем принудительным INSERT'ом.
        """
        async with SessionLocal() as db:
            log_entry = ActionLog(
                cluster_id=cluster_id,
                action_type="search",
            )
            db.add(log_entry)
            await db.commit()

    @staticmethod
    async def search_clusters_semantic(
        query: str,
        user_id: int,
        limit: int = 10,
    ) -> list[dict]:
        """
        Семантический поиск по кластерам через FRIDA-эмбеддинги + FAISS.
        Декомпозирует запрос на эмбеддинг, ищет ближайшие кластеры по сходству.
        Возвращает кластеры, отсортированные по убыванию сходства.
        """
        import numpy as np
        import faiss
        import asyncio

        # 1. Получаем все кластеры пользователя с саммари
        async with SessionLocal() as db:
            from sqlalchemy import select as sa_select
            stmt = (
                sa_select(Cluster)
                .where(Cluster.user_id == user_id)
                .order_by(Cluster.created_at.desc())
            )
            clusters = (await db.execute(stmt)).scalars().all()

        if not clusters:
            return []

        summaries = [c.summary or c.topic for c in clusters]

        # 2. Получаем эмбеддинги (в executor, т.к. синхронный код)
        def _get_embeddings(texts):
            from ai_agent.services import SummaryService
            svc = SummaryService()
            return svc.get_embeddings(texts)

        loop = asyncio.get_event_loop()
        all_texts = summaries + [query]
        all_embeddings = await loop.run_in_executor(None, _get_embeddings, all_texts)

        cluster_embeddings = all_embeddings[:-1]  # все кроме последнего
        query_embedding = all_embeddings[-1:]     # последний — запрос

        # 3. FAISS поиск ближайших
        d = cluster_embeddings.shape[1]
        index = faiss.IndexFlatIP(d)  # inner product (cosine similarity для нормализованных)
        faiss.normalize_L2(cluster_embeddings)
        faiss.normalize_L2(query_embedding)

        index.add(cluster_embeddings)
        k = min(limit, len(clusters))
        distances, indices = index.search(query_embedding, k)

        # 4. Формируем результат (открываем новую сессию для дат)
        results = []
        async with SessionLocal() as db2:
            for i, idx in enumerate(indices[0]):
                if idx < 0 or idx >= len(clusters):
                    continue
                c = clusters[idx]
                similarity = float(distances[0][i])

                # Даты новостей в кластере
                news_dates = await db2.execute(
                    sa_select(News.published_at)
                    .join(NewsCluster)
                    .where(NewsCluster.cluster_id == c.cluster_id)
                    .order_by(News.published_at)
                )
                dates = [row[0] for row in news_dates]
                date_from = dates[0].strftime("%Y-%m-%d") if dates else ""
                date_to = dates[-1].strftime("%Y-%m-%d") if dates else ""

                results.append({
                    "cluster_id": c.cluster_id,
                    "topic": c.topic,
                    "cluster_title": c.cluster_title or c.topic,
                    "summary": c.summary,
                    "news_sources": c.news_sources,
                    "created_at": c.created_at.isoformat(),
                    "date_from": date_from,
                    "date_to": date_to,
                    "similarity": round(similarity, 4),
                })

        return results

    @staticmethod
    async def build_chronology(cluster_id: int, user_login: str) -> dict:
        """
        Построение хронологии событий по кластеру.
        Выделяет ключевые этапы по времени и сохраняет в data/{login}/.
        """
        from pathlib import Path as _Path

        # 1. Получаем новости кластера
        async with SessionLocal() as db:
            cluster = await db.get(Cluster, cluster_id)
            if not cluster:
                return {"success": False, "error": "Кластер не найден"}

            news_rows = await db.execute(
                select(News)
                .join(NewsCluster)
                .where(NewsCluster.cluster_id == cluster_id)
                .order_by(News.published_at)
            )
            news_items = news_rows.scalars().all()

        if not news_items:
            return {"success": False, "error": "В кластере нет новостей"}

        # 2. Формируем данные для LLM
        news_lines = []
        for n in news_items:
            dt = n.published_at.strftime("%Y-%m-%d %H:%M") if n.published_at else "?"
            src = n.channel or "?"
            body = (n.news_body or "")[:200]
            news_lines.append(f"[{dt}] ({src}) {body}")

        combined = "\n\n".join(news_lines)

        # 3. LLM: выделяем ключевые этапы
        prompt = (
            "Прочитай следующие новости и построй хронологию событий. "
            "Выдели 3-7 ключевых этапов в хронологическом порядке. "
            "Для каждого этапа укажи:\n"
            "- Дату и время (если есть)\n"
            "- Краткое описание этапа (1 предложение)\n"
            "- Источники (каналы)\n\n"
            "Формат строго:\n"
            "YYYY-MM-DD HH:MM | 🔹 Описание этапа | Источники: канал1, канал2\n\n"
            f"Новости:\n{combined[:4000]}"
        )

        import aiohttp
        import backend.config as cfg

        # Функция fallback — ручная хронология по датам
        def _fallback_chronology(items):
            lines = []
            for n in items[:10]:
                dt = n.published_at.strftime("%Y-%m-%d %H:%M") if n.published_at else "?"
                src = n.channel or "?"
                body = (n.news_body or "")[:120]
                lines.append(f"{dt} | 🔹 {body} | Источники: {src}")
            return "\n".join(lines) if lines else "(нет данных)"

        payload = {
            "model": cfg.LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 1024, "temperature": 0.5},
        }

        chronology_text = ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    cfg.LLM_URL, json=payload,
                    timeout=aiohttp.ClientTimeout(total=180, connect=30),
                ) as resp:
                    if resp.status != 200:
                        chronology_text = _fallback_chronology(news_items)
                    else:
                        result = await resp.json()
                        chronology_text = result.get("message", {}).get("content", "").strip()
                        if not chronology_text:
                            chronology_text = _fallback_chronology(news_items)
        except aiohttp.ClientConnectorError:
            chronology_text = _fallback_chronology(news_items)
        except Exception:
            chronology_text = _fallback_chronology(news_items)

        # 4. Сохраняем в папку пользователя
        project_root = _Path(__file__).resolve().parent.parent.parent
        user_dir = project_root / "data" / user_login
        user_dir.mkdir(parents=True, exist_ok=True)

        topic_slug = (cluster.cluster_title or cluster.topic)[:50].replace(" ", "_").replace("/", "_")
        file_path = user_dir / f"chronology_{cluster_id}_{topic_slug}.txt"
        file_path.write_text(chronology_text, encoding="utf-8")

        # 5. Обновляем путь в БД
        async with SessionLocal() as db:
            c = await db.get(Cluster, cluster_id)
            if c:
                c.chronology_path = str(file_path)
                await db.commit()

        return {
            "success": True,
            "cluster_id": cluster_id,
            "chronology": chronology_text,
            "file_path": str(file_path),
        }

    @staticmethod
    async def delete_cluster(cluster_id: int) -> bool:
        """Удаляет кластер."""
        async with SessionLocal() as db:
            cluster = await db.get(Cluster, cluster_id)
            if not cluster:
                return False
            await db.delete(cluster)
            await db.commit()
            return True
