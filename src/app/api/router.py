from fastapi import APIRouter
from app.api.admin import crawler, movies_admin
from app.api.endpoints import movies, actresses, genres

api_router = APIRouter()

api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(actresses.router, prefix="/actresses", tags=["actresses"])
api_router.include_router(genres.router, prefix="/genres", tags=["genres"])

# 管理员路由
api_router.include_router(movies_admin.router, prefix="/admin/movies", tags=["movies-admin"])
api_router.include_router(crawler.router, prefix="/admin/crawler", tags=["crawler-admin"])