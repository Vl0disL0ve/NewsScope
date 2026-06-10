from fastapi import APIRouter
from .auth import router as auth_router
from .clusters import router as clusters_router
from .news import router as news_router
from .admin import router as admin_router
from .parser import router as parser_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(clusters_router)
router.include_router(news_router)
router.include_router(admin_router)
router.include_router(parser_router)