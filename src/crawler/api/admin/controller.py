from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import time
from datetime import datetime
from loguru import logger
from sqlalchemy import text, select, func
from crawler.repository.movie_repository import MovieRepository

# 导入服务模块
from crawler.service.movie_service import MovieService, CrawlerStatus
from crawler.service.movie_crawler_service import MovieCrawlerService
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
from app.config.database import async_session
from sqlalchemy.ext.asyncio import AsyncSession

# 创建路由器
router = APIRouter()

# 爬虫服务实例（延迟初始化）
movie_crawler_service = None  # 避免在导入时就创建浏览器实例

# 全局任务状态
task_status = {
    "is_running": False,
    "total_movies": 0,
    "processed_movies": 0,
    "success_count": 0,
    "failed_count": 0,
    "current_movie": "",
    "start_time": None,
    "end_time": None
}

# 响应模型
class TaskResponse(BaseModel):
    success: bool
    message: str
    task_id: str = None
    status: Dict[str, Any] = None

class MovieResponse(BaseModel):
    id: int
    original_id: int
    code: str
    title: str = None
    status: str
    language: str = None

# 获取电影服务实例
async def get_movie_service() -> MovieService:
    """FastAPI依赖项，用于获取MovieService实例
    
    使用async_session创建一个数据库会话，并将其注入到MovieService中
    """
    async with async_session() as session:
        yield MovieService(session)
        
# 获取电影详情爬虫服务实例
async def get_movie_detail_crawler_service() -> MovieDetailCrawlerService:
    """FastAPI依赖项，用于获取MovieDetailCrawlerService实例
    
    创建一个MovieDetailCrawlerService实例，注入所需依赖
    """
    from crawler.service.crawler_progress_service import CrawlerProgressService
    from crawler.repository.movie_repository import MovieRepository
    
    async with async_session() as session:
        progress_service = CrawlerProgressService(session)
        movie_repo = MovieRepository(session)
        yield MovieDetailCrawlerService(progress_service, movie_repo)

# 获取或创建爬虫服务实例
def get_crawler_service(headless: bool = True) -> MovieCrawlerService:
    """
    获取或创建爬虫服务实例
    
    Args:
        headless: 是否使用无头模式
        
    Returns:
        爬虫服务实例
    """
    global movie_crawler_service
    
    if movie_crawler_service is None:
        logger.info("创建新的爬虫服务实例")
        movie_crawler_service = MovieCrawlerService(headless=headless)
    
    return movie_crawler_service

@router.get("/movies", response_model=List[MovieResponse])
async def get_movies(
    status: str = Query(None, description="按状态筛选"),
    limit: int = Query(100, description="返回的最大记录数"),
    movie_service: MovieService = Depends(get_movie_service)
):
    """
    获取电影列表
    
    可以按状态筛选，默认返回所有状态的电影
    """
    try:
        movies = await movie_service.get_movies(status, limit)
        return movies
    except Exception as e:
        logger.error(f"获取电影列表时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取电影列表时出错: {str(e)}"
        )

@router.post("/start", response_model=TaskResponse)
async def start_crawler(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(10, description="批量处理的电影数量"),
    headless: bool = Query(True, description="是否使用无头模式"),
    movie_service: MovieService = Depends(get_movie_service)
):
    """
    启动电影爬虫
    
    在后台启动爬虫任务，爬取指定数量的电影
    """
    global task_status
    
    if task_status["is_running"]:
        return TaskResponse(
            success=False,
            message="爬虫任务已在运行中",
            status=task_status
        )
    
    # 重置任务状态
    task_status = {
        "is_running": True,
        "total_movies": batch_size,
        "processed_movies": 0,
        "success_count": 0,
        "failed_count": 0,
        "current_movie": "",
        "start_time": datetime.now().isoformat(),
        "end_time": None
    }
    
    # 添加后台任务
    background_tasks.add_task(
        run_crawler_task,
        batch_size,
        headless,
        movie_service
    )
    
    return TaskResponse(
        success=True,
        message=f"爬虫任务已启动，将处理 {batch_size} 部电影",
        task_id="movie_crawler",
        status=task_status
    )

@router.post("/crawl-movie-details", response_model=TaskResponse)
async def crawl_movie_details(
    background_tasks: BackgroundTasks,
    limit: int = Query(10, description="要爬取的电影数量"),
    language: str = Query("ja", description="爬取的语言版本，ja为日语，zh为中文"),
    headless: bool = Query(True, description="是否使用无头浏览器模式"),
    movie_detail_crawler_service: MovieDetailCrawlerService = Depends(get_movie_detail_crawler_service)
):
    """
    爬取电影详情
    
    查询需要爬取详情的电影，并在后台启动爬虫任务
    """
    global task_status
    
    if task_status["is_running"]:
        return TaskResponse(
            success=False,
            message="已有爬虫任务在运行中",
            status=task_status
        )
    
    # 查询需要爬取详情的电影代码
    async with async_session() as session:
        try:
            # 查询movie表中存在但movieinfo表中不存在的电影代码
            query = text("""
            SELECT m.id, m.code
            FROM movies m
            LEFT JOIN movie_info mi ON m.code = mi.code
            WHERE mi.code IS NULL AND m.code IS NOT NULL
            ORDER BY m.id ASC
            LIMIT :limit
            """)
            
            # Use MovieRepository pattern for database operations
            movie_repo = MovieRepository(session)
            result = await movie_repo.db.execute(query, {"limit": limit})
            movies_to_crawl = result.all()
            
            if not movies_to_crawl:
                return TaskResponse(
                    success=False,
                    message="没有找到需要爬取详情的电影",
                    task_id=None
                )
                
            # if movide_codes's suffix is 'Uncensored-Leaked', remove it only use prefix. GMEM-099-Uncensored-Leaked -> GMEM-099
            movie_codes = [
                movie.code.removesuffix("-Uncensored-Leaked") 
                for movie in movies_to_crawl 
            ]

            # 去重
            movie_codes = list(set(movie_codes))
            
            logger.info(f"找到 {len(movie_codes)} 部需要爬取详情的电影: {', '.join(movie_codes[:5])}...")
            
            # 重置任务状态
            task_status = {
                "is_running": True,
                "total_movies": len(movie_codes),
                "processed_movies": 0,
                "success_count": 0,
                "failed_count": 0,
                "current_movie": "",
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "movie_codes": movie_codes
            }
            
            # 添加后台任务
            background_tasks.add_task(
                run_movie_detail_crawler_task,
                movie_codes,
                language,
                headless,
                movie_detail_crawler_service
            )
            
            return TaskResponse(
                success=True,
                message=f"电影详情爬虫任务已启动，将爬取 {len(movie_codes)} 部电影的详情信息",
                task_id="movie_detail_crawler",
                status=task_status
            )
            
        except Exception as e:
            logger.error(f"启动电影详情爬虫时出错: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"启动电影详情爬虫时出错: {str(e)}"
            )

# 后台运行电影详情爬虫任务
async def run_movie_detail_crawler_task(
    movie_codes: List[str],
    language: str,
    headless: bool,
    movie_detail_crawler_service: MovieDetailCrawlerService
):
    """
    后台运行电影详情爬虫任务
    
    Args:
        movie_codes: 要爬取的电影代码列表
        language: 爬取的语言版本
        headless: 是否使用无头浏览器
        movie_detail_crawler_service: 电影详情爬虫服务实例
    """
    global task_status
    
    try:
        logger.info(f"开始爬取 {len(movie_codes)} 部电影的详情信息，语言: {language}")
        
        # 执行批量爬取
        results = await movie_detail_crawler_service.batch_crawl_movie_details(
            movie_codes=movie_codes,
            language=language,
            headless=headless
        )
        
        # 更新任务状态
        success_count = len(results)
        failed_count = len(movie_codes) - success_count
        
        task_status["is_running"] = False
        task_status["processed_movies"] = len(movie_codes)
        task_status["success_count"] = success_count
        task_status["failed_count"] = failed_count
        task_status["end_time"] = datetime.now().isoformat()
        
        logger.info(f"电影详情爬虫任务完成，成功: {success_count}，失败: {failed_count}")
        
    except Exception as e:
        logger.error(f"电影详情爬虫任务执行时出错: {str(e)}")
        task_status["is_running"] = False
        task_status["end_time"] = datetime.now().isoformat()
        task_status["error_message"] = str(e)

@router.get("/status", response_model=TaskResponse)
async def get_crawler_status():
    """
    获取爬虫任务状态
    
    返回当前爬虫任务的运行状态
    """
    global task_status
    
    return TaskResponse(
        success=True,
        message="获取爬虫状态成功",
        task_id="movie_crawler",
        status=task_status
    )

@router.post("/stop", response_model=TaskResponse)
async def stop_crawler():
    """
    停止爬虫任务
    
    强制停止当前运行的爬虫任务
    """
    global task_status, movie_crawler_service
    
    if not task_status["is_running"]:
        return TaskResponse(
            success=False,
            message="没有正在运行的爬虫任务",
            status=task_status
        )
    
    # 标记任务为停止状态
    task_status["is_running"] = False
    task_status["end_time"] = datetime.now().isoformat()
    
    # 关闭爬虫服务
    if movie_crawler_service:
        try:
            movie_crawler_service.close()
            movie_crawler_service = None
        except Exception as e:
            logger.error(f"关闭爬虫服务时出错: {e}")
    
    return TaskResponse(
        success=True,
        message="爬虫任务已停止",
        task_id="movie_crawler",
        status=task_status
    )

@router.post("/find-gaps", response_model=List[Dict[str, Any]])
async def find_movie_gaps(
    batch_size: int = Query(10, description="返回的最大记录数"),
    movie_service: MovieService = Depends(get_movie_service)
):
    """
    查找ID有间隔的电影记录
    
    用于查找数据库中ID有间隔的电影记录，以便进行爬取
    """
    try:
        gaps = await movie_service.find_movies_with_id_gaps(batch_size)
        return gaps
    except Exception as e:
        logger.error(f"查找ID间隔时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查找ID间隔时出错: {str(e)}"
        )

# 后台爬虫任务
async def run_crawler_task(batch_size: int, headless: bool, movie_service: MovieService):
    """
    运行爬虫任务
    
    在后台运行爬虫任务，爬取指定数量的电影
    
    Args:
        batch_size: 批量处理的电影数量
        headless: 是否使用无头模式
        movie_service: 电影服务实例
    """
    global task_status
    
    try:
        # 获取爬虫服务
        crawler_service = get_crawler_service(headless)
        
        # 查找ID有间隔的电影记录
        async with async_session() as session:
            movie_service = MovieService(session)
            gaps = await movie_service.find_movies_with_id_gaps(batch_size)
        
        if not gaps:
            logger.warning("没有找到ID间隔，爬虫任务结束")
            task_status["is_running"] = False
            task_status["end_time"] = datetime.now().isoformat()
            return
        
        # 更新任务状态
        task_status["total_movies"] = len(gaps)
        
        # 处理每个电影
        for i, movie in enumerate(gaps):
            if not task_status["is_running"]:
                logger.info("爬虫任务被手动停止")
                break
            
            # 更新当前处理的电影
            task_status["current_movie"] = movie["code"]
            
            try:
                # 添加电影记录
                async with async_session() as session:
                    movie_service = MovieService(session)
                    movie_id = await movie_service.add_movie(
                        code=movie["code"],
                        original_id=movie["original_id"],
                        status=CrawlerStatus.PROCESSING
                    )
                
                if movie_id < 0:
                    logger.error(f"添加电影记录失败: {movie['code']}")
                    task_status["failed_count"] += 1
                    continue
                
                # 爬取电影详情
                success = await crawler_service.crawl_movie(movie["code"], movie_id)
                
                # 更新电影状态
                async with async_session() as session:
                    movie_service = MovieService(session)
                    if success:
                        await movie_service.update_movie_status(movie_id, CrawlerStatus.COMPLETED)
                        task_status["success_count"] += 1
                    else:
                        await movie_service.update_movie_status(movie_id, CrawlerStatus.FAILED)
                        task_status["failed_count"] += 1
            
            except Exception as e:
                logger.error(f"处理电影 {movie['code']} 时出错: {e}")
                task_status["failed_count"] += 1
            
            # 更新进度
            task_status["processed_movies"] = i + 1
            
            # 随机延时，避免请求过于频繁
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"爬虫任务运行时出错: {e}")
    
    finally:
        # 标记任务为完成状态
        task_status["is_running"] = False
        task_status["end_time"] = datetime.now().isoformat()
        logger.info("爬虫任务结束")
