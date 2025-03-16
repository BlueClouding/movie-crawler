from fastapi import APIRouter
from crawler.api.admin import crawler_router

api_router = APIRouter()

# 管理员路由
api_router.include_router(crawler_router.router, prefix="/admin/crawler", tags=["crawler-admin"])