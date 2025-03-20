from fastapi import APIRouter
from crawler.api.admin import crawler_router
from crawler.api.schedules import movie_detail_job

api_router = APIRouter()

# 管理员路由
api_router.include_router(crawler_router.router, prefix="/admin/crawler", tags=["crawler-admin"])

# 爬虫任务路由
api_router.include_router(movie_detail_job.router, prefix="/schedules", tags=["schedules"])
