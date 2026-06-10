from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json

from app.database.session import get_db
from app.database.crud import ClusterCRUD, SettingsCRUD, HistoryCRUD, NewsCRUD
from app.services.cluster_service import ClusterService

router = APIRouter(prefix="/api/clusters", tags=["clusters"])

@router.post("/run/{user_id}")
async def run_clustering(user_id: int, num_clusters: int = None, db: AsyncSession = Depends(get_db)):
    settings_crud = SettingsCRUD(db)
    settings = await settings_crud.get(user_id)
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    k = num_clusters or settings.num_clusters
    
    end_date = settings.period_end or datetime.now()
    start_date = settings.period_start or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    channels = json.loads(settings.selected_channels) if settings.selected_channels else []
    
    cluster_service = ClusterService()
    result = await cluster_service.run_clustering(
        user_id=user_id,
        num_clusters=k,
        channels=channels,
        start_date=start_date,
        end_date=end_date
    )
    
    history_crud = HistoryCRUD(db)
    await history_crud.add(
        user_id=user_id,
        action_type="CLUSTER",
        action_params={"num_clusters": k, "channels": channels},
        result_preview=f"Создано {result.get('num_clusters', 0)} кластеров"
    )
    
    return result

@router.get("/results/{user_id}")
async def get_user_clusters(user_id: int, db: AsyncSession = Depends(get_db)):
    cluster_crud = ClusterCRUD(db)
    clusters = await cluster_crud.get_user_clusters(user_id)
    
    return {
        "clusters": [
            {
                "cluster_id": c.id,
                "topic": c.topic,
                "cluster_title": c.topic,
                "summary": c.summary,
                "news_count": c.news_count,
                "news_sources": c.news_sources,
                "audio_path": c.audio_path,
                "plot_path": c.plot_path,
                "chronology_path": c.chronology_path,
                "created_at": c.created_at.isoformat(),
                "date_from": c.period_start.isoformat() if c.period_start else None,
                "date_to": c.period_end.isoformat() if c.period_end else None
            }
            for c in clusters
        ]
    }

@router.get("/")
async def get_clusters(user_id: int = None, limit: int = 100, db: AsyncSession = Depends(get_db)):
    if user_id:
        cluster_crud = ClusterCRUD(db)
        clusters = await cluster_crud.get_user_clusters(user_id)
        return {"clusters": clusters[:limit]}
    return {"clusters": []}

@router.delete("/history")
async def clear_history(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    
    if token.startswith("user_"):
        parts = token.split("_")
        if len(parts) >= 2:
            user_id = int(parts[1])
            history_crud = HistoryCRUD(db)
            await history_crud.clear_user_history(user_id)
            return {"success": True, "message": "История очищена"}
    
    return {"success": False, "message": "Ошибка"}

@router.get("/search")
async def search_clusters(q: str, limit: int = 15, db: AsyncSession = Depends(get_db)):
    cluster_crud = ClusterCRUD(db)
    all_clusters = await cluster_crud.get_user_clusters(1)
    
    results = []
    query_lower = q.lower()
    
    for cluster in all_clusters:
        if query_lower in cluster.topic.lower() or query_lower in cluster.summary.lower():
            results.append({
                "cluster_id": cluster.id,
                "topic": cluster.topic,
                "cluster_title": cluster.topic,
                "summary": cluster.summary,
                "news_count": cluster.news_count,
                "news_sources": cluster.news_sources,
                "similarity": 0.8,
                "created_at": cluster.created_at.isoformat()
            })
    
    return {"clusters": results[:limit]}

@router.post("/{cluster_id}/tts")
async def generate_tts(cluster_id: int):
    return {"success": True, "audio_url": f"/static/audio/cluster_{cluster_id}.mp3"}

@router.post("/{cluster_id}/plot")
async def generate_plot(cluster_id: int):
    return HTMLResponse(content=f"<html><body><h1>График кластера {cluster_id}</h1><p>Заглушка</p></body></html>")

@router.post("/{cluster_id}/chronology")
async def generate_chronology(cluster_id: int):
    return {"success": True, "cluster_id": cluster_id, "chronology": "Хронология событий... (заглушка)"}

@router.post("/plot")
async def generate_all_plots():
    return HTMLResponse(content="<html><body><h1>Карта кластеров</h1><p>Заглушка</p></body></html>")

@router.post("/cluster")
async def cluster_from_front(
    request: Request,
    k: int,
    date_from: str,
    date_to: str,
    channels: str,
    db: AsyncSession = Depends(get_db)
):
    """Эндпоинт для фронта (без user_id в URL)"""
    # Получаем user_id из токена
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    
    user_id = None
    if token.startswith("user_"):
        parts = token.split("_")
        if len(parts) >= 2:
            user_id = int(parts[1])
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Парсим каналы
    import json as json_lib
    channel_list = json_lib.loads(channels)
    
    # Парсим даты
    from datetime import datetime
    start_date = datetime.strptime(date_from, "%Y-%m-%d")
    end_date = datetime.strptime(date_to, "%Y-%m-%d")
    
    # Сохраняем настройки
    settings_crud = SettingsCRUD(db)
    await settings_crud.update(
        user_id,
        num_clusters=k,
        selected_channels=[ch["name"] for ch in channel_list],
        period_start=start_date,
        period_end=end_date
    )
    
    # Запускаем кластеризацию
    cluster_service = ClusterService()
    result = await cluster_service.run_clustering(
        user_id=user_id,
        num_clusters=k,
        channels=[ch["name"] for ch in channel_list],
        start_date=start_date,
        end_date=end_date
    )
    
    return result