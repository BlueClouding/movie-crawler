from apscheduler.schedulers.asyncio import AsyncIOScheduler
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
from fastapi import APIRouter
import logging
import asyncio
from fastapi import Depends
from common.db.entity.movie import Movie
from typing import List
from crawler.repository.movie_repository import MovieRepository
from common.db.entity.download import DownloadUrl, WatchUrl
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session

# 获取日志记录器
logger = logging.getLogger(__name__)

# 初始化调度器
scheduler = AsyncIOScheduler()
# 保存当前的轮询间隔
current_polling_interval = 30.0

router = APIRouter()

# API端点：启动爬虫任务
@router.post("/start")
async def start_crawler(interval: float = 30.0, service: MovieDetailCrawlerService = Depends(MovieDetailCrawlerService),
movie_repository: MovieRepository = Depends(MovieRepository), session: AsyncSession = Depends(get_db_session)):
    global current_polling_interval
    current_polling_interval = interval
    
    # 删除现有的任务（如果有）
    if scheduler.get_job("movie_crawler"):
        scheduler.remove_job("movie_crawler")
    
    # 定义快速爬虫任务，完全自包含以避免依赖注入问题
    def run_crawler_job():
        async def process_movie_details():
            # 创建新的数据库会话
            
            movies : List[Movie] = await service.process_movies_details_once()
            
            # 更新进度
            await movie_repository.saveOrUpdate(movies, session)
            
            # 不需要显式提交
            logger.info("Successfully processed movie details in scheduled job")
    
        # 创建事件循环并运行任务
        try:
            # 创建新的事件循环（而不是使用FastAPI的循环）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 在这个完全新的循环中运行任务
            loop.run_until_complete(process_movie_details())
        except Exception as e:
            logger.error(f"Error setting up event loop in job: {str(e)}")
    
    # 添加新任务 - 使用自包含的爬虫任务函数
    scheduler.add_job(
        run_crawler_job,
        'interval', 
        seconds=interval,
        id="movie_crawler",
        replace_existing=True,
        max_instances=1
    )
    
    # 确保调度器已经启动
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started on-demand")
    
    return {"status": "success", "message": f"Crawler started with interval: {interval} seconds"}

# API端点：停止爬虫任务
@router.post("/stop")
async def stop_crawler():
    if scheduler.get_job("movie_crawler"):
        scheduler.remove_job("movie_crawler")
        return {"status": "success", "message": "Crawler stopped"}
    return {"status": "warning", "message": "Crawler was not running"}
