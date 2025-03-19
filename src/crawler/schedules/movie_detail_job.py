from apscheduler.schedulers.asyncio import AsyncIOScheduler
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
from crawler.repository.movie_repository import MovieRepository
from crawler.service.crawler_progress_service import CrawlerProgressService
from app.config.database import async_session
from fastapi import APIRouter
import logging
import asyncio
from fastapi import Depends

# 获取日志记录器
logger = logging.getLogger(__name__)

# 初始化调度器
scheduler = AsyncIOScheduler()
# 保存当前的轮询间隔
current_polling_interval = 30.0

router = APIRouter()

# API端点：启动爬虫任务
@router.post("/start")
async def start_crawler(interval: float = 10.0, movie_detail_crawler_service: MovieDetailCrawlerService = Depends(MovieDetailCrawlerService)):
    global current_polling_interval
    current_polling_interval = interval
    
    # 删除现有的任务（如果有）
    if scheduler.get_job("movie_crawler"):
        scheduler.remove_job("movie_crawler")
    
    # 定义快速爬虫任务，完全自包含以避免依赖注入问题
    def run_crawler_job():
        async def process_movie_details():
            # 创建新的数据库会话，而不是使用FastAPI的注入系统
            async with async_session() as session:
                try:
                    # 手动创建仓库和服务，使用新数据库会话
                    movie_repo = MovieRepository(session)
                    progress_service = CrawlerProgressService(session)
                    service = MovieDetailCrawlerService(progress_service, movie_repo)
                    
                    # 执行爬虫处理
                    await service.process_movies_details_once(session)
                    await session.commit()
                    logger.info("Successfully processed movie details in scheduled job")
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error in movie crawler scheduled task: {str(e)}")
                    # 记录完整的堆栈跟踪以便调试
                    import traceback
                    logger.error(traceback.format_exc())
        
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
        replace_existing=True
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
