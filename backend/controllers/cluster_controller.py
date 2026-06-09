# -*- coding: utf-8 -*-
"""
ClusterController — API-роуты для управления кластерами новостей.
"""

import sys
from pathlib import Path
from typing import Optional

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from datetime import time as dt_time

from backend.services.cluster_service import ClusterService
from backend.services.news_service import NewsService
from backend.deps import get_current_user
from backend.config import LLM_URL, LLM_MODEL

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


# ─── Pydantic-схемы ───────────────────────────────────────────

class CreateClusterRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=1)
    news_ids: list[int] = Field(..., min_length=1)
    news_sources: list[str] = Field(...)


# ─── Роуты ────────────────────────────────────────────────────

@router.get("/")
async def list_clusters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Получение списка кластеров текущего пользователя."""
    service = ClusterService()
    clusters = await service.get_clusters_by_user(
        user_id=current_user["user_id"],
        skip=skip,
        limit=limit,
    )
    return {"total": len(clusters), "clusters": clusters}


@router.get("/{cluster_id}")
async def get_cluster(
    cluster_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Детальная информация о кластере."""
    service = ClusterService()
    cluster = await service.get_cluster_detail(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if cluster["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return cluster


@router.post("/")
async def create_cluster(
    data: CreateClusterRequest,
    current_user: dict = Depends(get_current_user),
):
    """Создание нового кластера с привязкой новостей."""
    service = ClusterService()
    cluster = await service.create_cluster(
        user_id=current_user["user_id"],
        topic=data.topic,
        summary=data.summary,
        news_ids=data.news_ids,
        news_sources=data.news_sources,
    )
    return cluster


@router.delete("/{cluster_id}")
async def delete_cluster(
    cluster_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Удаление кластера."""
    service = ClusterService()
    cluster = await service.get_cluster_detail(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if cluster["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    deleted = await service.delete_cluster(cluster_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Ошибка удаления")
    return {"success": True}


@router.post("/{cluster_id}/summarize")
async def summarize_cluster(
    cluster_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Запуск генерации краткого пересказа кластера через LLM."""
    service = ClusterService()
    cluster = await service.get_cluster_detail(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if cluster["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    # Собираем тексты новостей в один
    texts = [n["news_body"] for n in cluster["news_items"]]
    combined = "\n\n".join(texts)

    try:
        from ai_agent.services import SummaryService
        summarizer = SummaryService(llm_url=LLM_URL, llm_model=LLM_MODEL)
        summary = await summarizer.summarize_with_llm(combined)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка суммаризации: {e}")

    await service.update_cluster_summary(cluster_id, summary)
    return {"cluster_id": cluster_id, "summary": summary}


@router.post("/{cluster_id}/tts")
async def generate_audio(
    cluster_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Генерация аудио-пересказа кластера (TTS)."""
    service = ClusterService()
    cluster = await service.get_cluster_detail(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if cluster["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    if not cluster["summary"]:
        raise HTTPException(status_code=400, detail="Сначала создайте суммаризацию")

    # Если аудио уже есть — переиспользуем
    if cluster.get("audio_path") and Path(cluster["audio_path"]).is_file():
        audio_url = f"/api/audio/{cluster_id}"
        return {"cluster_id": cluster_id, "audio_url": audio_url, "reused": True}

    try:
        from ai_agent.services import TTSService
        tts = TTSService()
        user_dir = str(Path(_project_root) / "data" / "audio" / current_user["login"])
        audio_path = await tts.text_to_speech(cluster["summary"], cluster_id, user_dir)
        # Проверяем, что файл реально создался
        if not Path(audio_path).is_file():
            raise RuntimeError(f"Файл {audio_path} не был создан. Убедитесь, что edge-tts работает (требуется интернет).")
    except ImportError:
        raise HTTPException(status_code=500, detail="edge-tts не установлен. Выполните: pip install edge-tts")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка TTS: {e}")

    await service.set_audio_path(cluster_id, audio_path)
    # Возвращаем URL для воспроизведения
    audio_url = f"/api/audio/{cluster_id}"
    return {"cluster_id": cluster_id, "audio_url": audio_url, "audio_path": audio_path}


@router.post("/{cluster_id}/plot")
async def generate_plot(
    cluster_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Генерирует HTML-график распределения новостей в кластере."""
    service = ClusterService()
    cluster = await service.get_cluster_detail(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if cluster["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    try:
        from collections import Counter
        import plotly.express as px

        news = cluster.get("news_items", [])
        if not news:
            raise HTTPException(status_code=400, detail="Нет новостей для графика")

        # Считаем количество по каналам
        channel_counts = Counter(n["channel"] for n in news)
        channels_sorted = sorted(channel_counts.items(), key=lambda x: -x[1])

        fig = px.bar(
            x=[c[0] for c in channels_sorted],
            y=[c[1] for c in channels_sorted],
            title=f"Распределение новостей по каналам — Кластер {cluster_id}",
            labels={"x": "Канал", "y": "Количество"},
            color=[c[0] for c in channels_sorted],
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(
            template="plotly_white",
            showlegend=False,
            height=400,
            xaxis_tickangle=-45,
        )

        # Возвращаем HTML
        html = fig.to_html(include_plotlyjs="cdn")
        return HTMLResponse(content=html)

    except ImportError:
        raise HTTPException(status_code=500, detail="plotly не установлен. pip install plotly")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка графика: {e}")


@router.post("/plot")
async def generate_clusters_plot(
    current_user: dict = Depends(get_current_user),
):
    """
    Интерактивный scatter plot всех кластеров пользователя.
    Каждая точка — новость; цвет = кластер; границы — линии;
    размер кластера зависит от количества новостей; при наведении — саммари.
    """
    import numpy as np
    import asyncio
    from sklearn.decomposition import PCA

    service = ClusterService()
    clusters = await service.get_clusters_by_user(
        user_id=current_user["user_id"], limit=50
    )

    if not clusters:
        raise HTTPException(status_code=400, detail="Нет кластеров для графика")

    # Собираем все новости с их эмбеддингами
    all_texts = []
    cluster_labels = []
    cluster_summaries = {}
    news_meta = []

    for ci, c in enumerate(clusters):
        detail = await service.get_cluster_detail(c["cluster_id"])
        if not detail:
            continue
        for n in detail.get("news_items", []):
            body = n.get("news_body", "")[:200]
            if body.strip():
                all_texts.append(body)
                cluster_labels.append(ci)
                news_meta.append({
                    "channel": n.get("channel", ""),
                    "date": n.get("published_at", "")[:16],
                })
        cluster_summaries[ci] = (c.get("cluster_title") or c.get("topic", ""))[:50]

    if len(all_texts) < 2:
        raise HTTPException(status_code=400, detail="Недостаточно новостей для визуализации")

    # Получаем эмбеддинги и снижаем размерность до 2D
    def _get_2d(texts):
        from ai_agent.services import SummaryService
        svc = SummaryService()
        emb = svc.get_embeddings(texts)
        pca = PCA(n_components=2, random_state=42)
        return pca.fit_transform(emb), pca

    loop = asyncio.get_event_loop()
    coords_2d, _ = await loop.run_in_executor(None, _get_2d, all_texts)

    # Строим scatter plot через plotly
    import plotly.graph_objects as go
    import plotly.express as px

    fig = go.Figure()

    unique_clusters = sorted(set(cluster_labels))
    colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2
    if len(unique_clusters) > len(colors):
        colors = colors * (len(unique_clusters) // len(colors) + 1)

    for ci in unique_clusters:
        indices = [i for i, lbl in enumerate(cluster_labels) if lbl == ci]
        cluster_coords = coords_2d[indices]
        summary = cluster_summaries.get(ci, "")[:50]

        # Размер маркера зависит от количества новостей
        marker_size = max(6, min(16, 6 + len(indices) * 0.5))

        hover_texts = []
        for i in indices:
            meta = news_meta[i]
            hover_texts.append(f"{meta['channel']}<br>{meta['date']}<br>{all_texts[i][:100]}...")

        fig.add_trace(go.Scatter(
            x=cluster_coords[:, 0],
            y=cluster_coords[:, 1],
            mode="markers",
            name=f"Кластер {ci+1}: {summary}...",
            marker=dict(
                size=marker_size,
                color=colors[ci % len(colors)],
                line=dict(width=1, color="white"),
                opacity=0.8,
            ),
            text=hover_texts,
            hoverinfo="text",
        ))

        # Граница кластера — выпуклая оболочка (convex hull)
        if len(indices) >= 3:
            from scipy.spatial import ConvexHull
            try:
                hull = ConvexHull(cluster_coords)
                hull_x = list(cluster_coords[hull.vertices, 0]) + [cluster_coords[hull.vertices[0], 0]]
                hull_y = list(cluster_coords[hull.vertices, 1]) + [cluster_coords[hull.vertices[0], 1]]
                fig.add_trace(go.Scatter(
                    x=hull_x, y=hull_y,
                    mode="lines",
                    line=dict(color=colors[ci % len(colors)], width=1.5, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ))
            except Exception:
                pass

    fig.update_layout(
        title="Карта кластеров новостей",
        template="plotly_white",
        height=650,
        hovermode="closest",
        xaxis=dict(title="PCA-1", showgrid=False, zeroline=False),
        yaxis=dict(title="PCA-2", showgrid=False, zeroline=False),
        legend=dict(x=1.02, y=1, font=dict(size=10)),
    )

    html = fig.to_html(include_plotlyjs="cdn")
    return HTMLResponse(content=html)


@router.get("/search")
async def search_clusters(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """
    Семантический поиск по кластерам через FRIDA-эмбеддинги.
    При ошибке ML-модели — fallback на текстовый поиск (ILIKE).
    """
    service = ClusterService()
    try:
        results = await service.search_clusters_semantic(
            query=q,
            user_id=current_user["user_id"],
            limit=limit,
        )
    except Exception as e:
        # Fallback: текстовый поиск по саммари и темам кластеров
        from database.init_db import SessionLocal
        from database.models import Cluster
        from sqlalchemy import or_
        async with SessionLocal() as db:
            stmt = (
                select(Cluster)
                .where(Cluster.user_id == current_user["user_id"])
                .where(
                    or_(
                        Cluster.topic.ilike(f"%{q}%"),
                        Cluster.summary.ilike(f"%{q}%"),
                        Cluster.cluster_title.ilike(f"%{q}%"),
                    )
                )
                .order_by(Cluster.created_at.desc())
                .limit(limit)
            )
            clusters = (await db.execute(stmt)).scalars().all()
        results = [
            {
                "cluster_id": c.cluster_id,
                "topic": c.topic,
                "cluster_title": c.cluster_title or c.topic,
                "summary": c.summary,
                "news_sources": c.news_sources,
                "created_at": c.created_at.isoformat(),
                "similarity": 0.0,
            }
            for c in clusters
        ]

    # Логируем поиск
    if results:
        await service.log_search_action(
            user_id=current_user["user_id"],
            cluster_id=results[0]["cluster_id"],
            query=q,
        )
    return {"total": len(results), "clusters": results}


@router.delete("/history")
async def clear_history(current_user: dict = Depends(get_current_user)):
    """
    Очистка истории пользователя: удаляет все кластеры текущего пользователя.
    Логи сервера (entry_log, actions_log) не затрагиваются.
    """
    from database.init_db import SessionLocal
    from database.models import Cluster, ActionLog
    from sqlalchemy import delete

    async with SessionLocal() as db:
        # Получаем ID кластеров пользователя
        cluster_ids = (await db.execute(
            select(Cluster.cluster_id).where(Cluster.user_id == current_user["user_id"])
        )).scalars().all()

        deleted = len(cluster_ids)

        # Каскадное удаление: NewsCluster и ActionLog удалятся по FK CASCADE
        for cid in cluster_ids:
            cluster = await db.get(Cluster, cid)
            if cluster:
                await db.delete(cluster)

        await db.commit()

    return {"success": True, "deleted_clusters": deleted, "message": f"Удалено {deleted} записей истории"}


@router.post("/{cluster_id}/chronology")
async def build_chronology(
    cluster_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Построение хронологии событий по кластеру.
    Сохраняет результат в data/{login}/ и возвращает текст.
    """
    service = ClusterService()
    cluster = await service.get_cluster_detail(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Кластер не найден")
    if cluster["user_id"] != current_user["user_id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    result = await service.build_chronology(
        cluster_id=cluster_id,
        user_login=current_user["login"],
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Ошибка"))
    return result


@router.post("/cluster")
async def auto_cluster(
    source: Optional[str] = Query(None, description="Источник новостей"),
    k: int = Query(5, ge=2, le=50, description="Количество кластеров"),
    channels: Optional[str] = Query(None, description="Выбранные каналы через запятую"),
    date_from: Optional[str] = Query(None, description="Дата с (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата по (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Автоматическая кластеризация новостей через ML.
    Если в channels есть Lenta.ru — парсер запускается автоматически.
    """

    # ─── Авто-парсинг выбранных каналов ──────────────────────
    if date_from:
        dt_from_date = datetime.fromisoformat(date_from).date()
        dt_from = datetime.combine(dt_from_date, dt_time.min, tzinfo=timezone.utc)
    else:
        dt_from = None

    if date_to:
        dt_to_date = datetime.fromisoformat(date_to).date()
        dt_to = datetime.combine(dt_to_date, dt_time.max, tzinfo=timezone.utc)
    else:
        dt_to = None

    channel_names = []    # названия каналов для фильтра
    if channels:
        import json as _json
        try:
            channel_list = _json.loads(channels)
        except _json.JSONDecodeError:
            channel_list = [{"name": c.strip()} for c in channels.split(",") if c.strip()]

        from backend.services.parser_service import LentaParser, TelegramChannelParser

        tg_channels = []
        for ch in channel_list:
            ch_name = ch.get("name", "")
            channel_names.append(ch_name)
            if ch.get("source") == "lenta" or ch_name == "Lenta.ru":
                try:
                    parser = LentaParser()
                    news = await parser.fetch_news()
                    await parser.save_news(news)
                except Exception as e:
                    print(f"  ⚠️  Lenta.ru: {e}")
            elif ch.get("source") == "tg" and ch.get("tg_user"):
                tg_channels.append(ch["tg_user"])

        if tg_channels:
            try:
                tg_parser = TelegramChannelParser()
                tg_news = await tg_parser.fetch_multiple_channels(tg_channels)
                await tg_parser.save_news(tg_news)
            except Exception as e:
                print(f"  ⚠️  Telegram: {e}")

    cluster_svc = ClusterService()
    news_svc = NewsService()
    warning = None

    # Фильтр: каналы + даты
    news_list = await news_svc.get_news(
        channels=channel_names if channel_names else None,
        date_from=dt_from,
        date_to=dt_to,
        limit=500,
    )

    if len(news_list) < k:
        warning = f"Каналы: {channel_names}, найдено {len(news_list)} новостей (нужно {k})."
        if len(news_list) < 2:
            return {"total": 0, "clusters": [],
                    "warning": warning}
        k = len(news_list)

    texts = [n["news_body"] for n in news_list]
    ids = [n["news_id"] for n in news_list]

    # Вся ML-логика в отдельной синхронной функции для run_in_executor
    def _run_clustering(texts, k):
        from ai_agent.services import SummaryService
        svc = SummaryService()
        emb = svc.get_embeddings(texts)
        return svc.cluster_with_faiss(emb, k)

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        clusters = await loop.run_in_executor(None, _run_clustering, texts, k)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Ошибка кластеризации: {e}\n{traceback.format_exc()}")

    from ai_agent.services import SummaryService

    cluster_svc = ClusterService()
    results = []

    for cluster_label, indices in clusters.items():
        news_ids_in_cluster = [ids[i] for i in indices]
        cluster_texts = [texts[i] for i in indices if texts[i].strip()]
        news_items = [news_list[i] for i in indices]

        # Источники — названия каналов
        channel_names = list(set(n["channel"] for n in news_items))

        # Тема кластера — первые слова первой новости
        topic_text = (cluster_texts[0][:80] + "...") if cluster_texts else "Новости"

        # Краткий пересказ и название темы (если есть текст)
        combined = "\n\n".join(cluster_texts[:10]) if cluster_texts else ""
        if len(combined) < 50:
            cluster_title = "Новости"
            summary = f"Кластер из {len(news_ids_in_cluster)} новостей."
        else:
            try:
                llm = SummaryService(load_embeddings=False, llm_url=LLM_URL, llm_model=LLM_MODEL)
                cluster_title, summary = await llm.summarize_with_llm(combined)
            except Exception:
                cluster_title = "Новости"
                summary = f"Кластер из {len(news_ids_in_cluster)} новостей."

        # Тема — короткое название от LLM или первые слова
        topic_text = cluster_texts[0][:80] if cluster_texts else "Новости"

        cluster = await cluster_svc.create_cluster(
            user_id=current_user["user_id"],
            topic=topic_text,
            cluster_title=cluster_title,
            summary=summary,
            news_ids=news_ids_in_cluster,
            news_sources=channel_names,
        )
        results.append(cluster)

    resp = {"total": len(results), "clusters": results}
    if warning:
        resp["warning"] = warning
    return resp
