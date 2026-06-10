from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database.session import get_db
from app.database.crud import UserCRUD, StatsCRUD

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats/database")
async def get_db_stats(db: AsyncSession = Depends(get_db)):
    stats_crud = StatsCRUD(db)
    return await stats_crud.get_db_stats()

@router.get("/stats/visits")
async def get_visits_stats(interval: str = "week", db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    
    if interval == "day":
        start = now - timedelta(days=1)
    elif interval == "week":
        start = now - timedelta(days=7)
    elif interval == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=7)
    
    stats_crud = StatsCRUD(db)
    visits = await stats_crud.get_visits_by_period(start, now)
    
    return [{"label": str(v[0]), "value": v[1]} for v in visits]

@router.get("/users/search")
async def search_users(q: str, db: AsyncSession = Depends(get_db)):
    user_crud = UserCRUD(db)
    users = await user_crud.get_all_users()
    
    results = []
    for user in users:
        if q.lower() in user.login.lower():
            results.append({"user_id": user.id, "login": user.login})
    
    return results[:10]

@router.get("/stats/users")
async def get_users_stats(interval: str = "day", db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timedelta
    now = datetime.now()
    
    if interval == "day":
        start = now - timedelta(days=1)
    elif interval == "week":
        start = now - timedelta(days=7)
    elif interval == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=7)
    
    stats_crud = StatsCRUD(db)
    users = await stats_crud.get_new_users_by_period(start, now)
    
    result = []
    for date, count in users:
        if isinstance(date, datetime):
            label = date.strftime("%Y-%m-%d")
        else:
            label = str(date)
        result.append({"label": label, "value": count})
    
    return result