from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.session import get_db
from app.services.auth_service import AuthService
from app.database.crud import UserCRUD, SettingsCRUD

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    login: str
    password: str

class RegisterRequest(BaseModel):
    login: str
    password: str
    role: str = "user"

@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    result = await auth_service.login(request.login, request.password, "WEB")
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    
    token = f"user_{result['user_id']}_{result['login']}"
    
    return {
        "success": True,
        "token": token,
        "role": result["role"],
        "user_id": result["user_id"]
    }

@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user_crud = UserCRUD(db)
    existing = await user_crud.get_by_login(request.login)
    if existing:
        raise HTTPException(status_code=400, detail="Логин уже занят")
    
    auth_service = AuthService(db)
    password_hash = auth_service.hash_password(request.password)
    user = await user_crud.create(request.login, password_hash, request.role)
    
    return {"success": True, "user_id": user.id, "login": user.login}

@router.post("/login/tg")
async def login_tg(tg_uuid: str, db: AsyncSession = Depends(get_db)):
    user_crud = UserCRUD(db)
    user = await user_crud.get_by_tg_id(int(tg_uuid)) if tg_uuid.isdigit() else None
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    token = f"tg_{user.id}_{user.login}"
    
    return {"success": True, "token": token, "role": user.role}

@router.get("/settings")
async def get_settings(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    
    if token.startswith("user_"):
        parts = token.split("_")
        if len(parts) >= 2:
            user_id = int(parts[1])
            settings_crud = SettingsCRUD(db)
            settings = await settings_crud.get(user_id)
            return {
                "cluster_count": settings.num_clusters if settings else 10,
                "channels": settings.selected_channels if settings else []
            }
    
    return {"cluster_count": 10, "channels": []}

@router.post("/settings")
async def save_settings(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    
    if token.startswith("user_"):
        parts = token.split("_")
        if len(parts) >= 2:
            user_id = int(parts[1])
            settings_crud = SettingsCRUD(db)
            await settings_crud.update(
                user_id,
                num_clusters=data.get("cluster_count", 10),
                selected_channels=data.get("channels", [])
            )
            return {"success": True}
    
    return {"success": False}