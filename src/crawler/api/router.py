from fastapi import APIRouter
from crawler.api.admin import crawler_router, movies_admin

api_router = APIRouter()

# 管理员路由
api_router.include_router(movies_admin.router, prefix="/admin/movies", tags=["movies-admin"])
api_router.include_router(crawler_router.router, prefix="/admin/crawler", tags=["crawler-admin"])