from fastapi import APIRouter
import logging
import asyncio
import threading
from fastapi import Depends
from common.db.entity.movie import Movie
from typing import List
from crawler.repository.movie_repository import MovieRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService

# 获取日志记录器
logger = logging.getLogger(__name__)

# 控制后台任务的标志
crawler_running = False
crawler_thread = None

router = APIRouter()

# API端点：启动爬虫任务
@router.post("/start")
async def start_crawler():
    global crawler_running, crawler_thread
    
    # 如果爬虫已经在运行，返回提示信息
    if crawler_running and crawler_thread and crawler_thread.is_alive():
        return {"status": "warning", "message": "Crawler is already running"}
    
    # 设置运行标志
    crawler_running = True
    
    # 定义后台爬虫任务，完全自包含以避免依赖注入问题
    def run_crawler_background():
        async def continuous_crawler():
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 导入所需的模块
            from app.config.database import async_session
            from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
            from crawler.repository.movie_repository import MovieRepository
            from crawler.service.crawler_progress_service import CrawlerProgressService
            from app.repositories.genre_repository import GenreRepository
            from crawler.repository.page_crawler_repository import PageCrawlerRepository
            from crawler.repository.movie_crawler_repository import MovieCrawlerRepository
            from crawler.repository.crawler_progress_repository import CrawlerProgressRepository
            
            # 持续运行爬虫，直到被停止
            while crawler_running:
                try:
                    # 为每个循环创建新的数据库会话
                    async with async_session() as new_session:
                        try:
                            # 创建所需的仓库实例
                            new_repository = MovieRepository(new_session)
                            genre_repository = GenreRepository(new_session)
                            page_crawler_repository = PageCrawlerRepository(new_session)
                            movie_crawler_repository = MovieCrawlerRepository(new_session)
                            crawler_progress_repository = CrawlerProgressRepository(new_session)
                            
                            # 创建 CrawlerProgressService 实例
                            crawler_progress_service = CrawlerProgressService(
                                genre_repository=genre_repository,
                                page_crawler_repository=page_crawler_repository,
                                movie_crawler_repository=movie_crawler_repository,
                                crawler_progress_repository=crawler_progress_repository
                            )
                            
                            # 创建 MovieDetailCrawlerService 实例
                            new_service = MovieDetailCrawlerService(
                                crawler_progress_service=crawler_progress_service,
                                movie_repository=new_repository
                            )
                            
                            # 获取并处理电影详情
                            try:
                                movies: List[Movie] = await new_service.process_movies_details_once(1)
                                
                                # 如果没有电影需要处理，等待一段时间后再尝试
                                if not movies or len(movies) == 0:
                                    logger.info("No movies to process, waiting for 10 seconds before next attempt")
                                    await asyncio.sleep(10)
                                    continue
                                
                                # 处理每个电影，为每个电影使用单独的事务
                                processed_count = 0
                                for movie in movies:
                                    # 为每个电影创建一个新的事务
                                    try:
                                        # 尝试保存电影
                                        await new_repository.saveOrUpdate([movie], new_session)
                                        # 立即提交这个电影的事务
                                        await new_session.commit()
                                        processed_count += 1
                                    except Exception as movie_error:
                                        logger.error(f"Error saving movie {movie.code if hasattr(movie, 'code') else 'unknown'}: {str(movie_error)}")
                                        # 回滚事务并继续处理下一个电影
                                        await new_session.rollback()
                                        continue
                                
                                logger.info(f"Successfully processed {processed_count} out of {len(movies)} movies in background task")
                            except Exception as process_error:
                                logger.error(f"Error processing movies: {str(process_error)}")
                                # 回滚事务
                                await new_session.rollback()
                                # 等待一段时间后继续
                                await asyncio.sleep(5)
                        except Exception as session_error:
                            logger.error(f"Error setting up services: {str(session_error)}")
                            # 尝试回滚事务
                            try:
                                await new_session.rollback()
                            except:
                                pass  # 忽略回滚错误
                    
                except Exception as e:
                    logger.error(f"Error in continuous crawler: {str(e)}")
                    # 出错后等待一段时间再继续
                    await asyncio.sleep(5)
        
        # 运行连续爬虫任务
        try:
            asyncio.run(continuous_crawler())
        except Exception as e:
            logger.error(f"Error in crawler background thread: {str(e)}")
            # 确保标志被重置
            global crawler_running
            crawler_running = False
    
    # 创建并启动后台线程
    crawler_thread = threading.Thread(target=run_crawler_background, daemon=True)
    crawler_thread.start()
    
    logger.info("Background crawler started")
    return {"status": "success", "message": "Continuous crawler started in background"}

# API端点：停止爬虫任务
@router.post("/stop")
async def stop_crawler():
    global crawler_running, crawler_thread
    
    if crawler_running and crawler_thread and crawler_thread.is_alive():
        # 设置标志以停止爬虫循环
        crawler_running = False
        
        # 等待线程结束（最多等待5秒）
        crawler_thread.join(timeout=5)
        
        # 检查线程是否已结束
        if crawler_thread.is_alive():
            logger.warning("Crawler thread did not terminate gracefully within timeout")
        else:
            logger.info("Crawler thread terminated successfully")
        
        return {"status": "success", "message": "Crawler stopped"}
    
    return {"status": "warning", "message": "Crawler was not running"}
