import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from crawler.models.request.crawler_request import CrawlerRequest
from common.db.entity.crawler import (
    CrawlerProgress,
    CrawlerProgressCreate,
    CrawlerProgressResponse, 
    PagesProgressCreate, PagesProgressResponse,
    CrawlerProgressSummary
)
from crawler.service.crawler_service import CrawlerService


# 获取日志记录器
logger = logging.getLogger(__name__)

class Start(str, Enum):
    GENRES = "genres"
    GENRES_PAGES = "genres_pages"
    MOVIES = "movies"
    ACTRESSES = "actresses"



class CrawlerResponse(BaseModel):
    task_id: int
    status: str
    message: str

router = APIRouter()

@router.post("/start", response_model=CrawlerResponse)
async def start_crawler(request: CrawlerRequest, 
    crawler_service: CrawlerService = Depends()):
    """Start the crawler with specified parameters."""
    
    # Start crawler in background task
    task : CrawlerProgress = await crawler_service.create_crawler_progress(CrawlerProgress(
        task_type="movie_crawler",
        status="pending",
    ))
    
    logger.info(f"爬虫进度记录创建成功，ID: {task.id}")
    
    # Initialize crawler in background
    logger.debug(f"初始化爬虫，类型: {request.start}")
    
    switch = {
        Start.GENRES: crawler_service.initialize_and_startGenres,
        Start.GENRES_PAGES: crawler_service.initialize_and_startGenresPages
    }
    
    # 检查请求的启动类型是否有效
    if request.start not in switch:
        logger.error(f"无效的爬虫启动类型: {request.start}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid crawler start type: {request.start}"
        )
    
    # 获取对应的启动函数
    start_function = switch[request.start]
    
    # 调用启动函数
    logger.info(f"开始执行爬虫启动函数: {start_function.__name__}")
    await start_function(task.id)
    
    logger.info(f"爬虫启动成功，任务ID: {task.id}")
    return CrawlerResponse(
        task_id=task.id,
        status="started",
        message="Crawler started successfully"
    )

@router.delete("/stop/{task_id}")
async def stop_crawler(
    task_id: int = Path(..., title="The ID of the crawler task"),
    crawler_service: CrawlerService = Depends()
):
    """Stop a running crawler task."""
    # 获取任务信息
    logger.debug(f"获取任务信息，ID: {task_id}")
    task = await crawler_service.get_by_id(task_id)
    
    # 检查任务是否存在
    if not task:
        logger.warning(f"任务不存在，ID: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found"
        )
        
    # 检查任务状态
    if task.status == "completed":
        logger.warning(f"任务已完成，无法停止，ID: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Task already completed"
        )
        
    # 更新任务状态
    logger.info(f"更新任务状态为已停止，ID: {task_id}")
    await crawler_service.update_status(task_id, "stopped")
    
    logger.info(f"任务已成功停止，ID: {task_id}")
    return {"message": "Task stopped successfully"}

@router.get("/progress", response_model=List[CrawlerProgressResponse])
async def get_crawler_progress( # Added async
    crawler_service: CrawlerService = Depends()
):
    """
    Get all crawler progress records.
    """
    return await crawler_service.get_all()

@router.post("/progress", response_model=CrawlerProgressResponse)
async def create_crawler_progress( # Added async
    crawler_in: CrawlerProgressCreate,
    crawler_service: CrawlerService = Depends()
):
    """
    Create a new crawler progress record.
    """
    return await crawler_service.create(crawler_in.dict())

@router.get("/progress/{crawler_id}", response_model=CrawlerProgressResponse)
async def get_crawler_progress_by_id( # Added async
    crawler_id: int = Path(..., title="The ID of the crawler progress to get"),
    crawler_service: CrawlerService = Depends()
):
    """
    Get crawler progress by ID.
    """
    crawler = await crawler_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return crawler

@router.put("/progress/{crawler_id}/status", response_model=CrawlerProgressResponse)
async def update_crawler_status( # Added async
    status: str = Query(..., title="New status"),
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    crawler_service: CrawlerService = Depends()
):
    """
    Update crawler progress status.
    """
    crawler = await crawler_service.update_status(crawler_id, status)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return crawler

@router.get("/progress/{crawler_id}/pages", response_model=List[PagesProgressResponse])
async def get_pages_progress( # Added async
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    crawler_service: CrawlerService = Depends()
):
    """
    Get all pages progress for a crawler.
    """
    crawler = await crawler_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return await crawler_service.get_pages_progress(crawler_id)

@router.post("/progress/{crawler_id}/pages", response_model=PagesProgressResponse)
async def create_page_progress( # Added async
    page_in: PagesProgressCreate,
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    crawler_service: CrawlerService = Depends()
):
    """
    Create a new page progress record.
    """
    crawler = await crawler_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )

    page_data = page_in.dict()
    page_data["crawler_progress_id"] = crawler_id

    return await services.pages_progress_service.create(page_data) # Added await

@router.put("/pages/{page_id}/progress", response_model=PagesProgressResponse)
async def update_page_progress( # Added async
    processed_items: int = Query(..., ge=0, title="Number of processed items"),
    status: str = Query(None, title="New status"),
    page_id: int = Path(..., title="The ID of the page progress"),
    crawler_service: CrawlerService = Depends()
):
    """
    Update page progress.
    """
    page = await crawler_service.update_progress(page_id, processed_items, status)
    if not page:
        raise HTTPException(
            status_code=404,
            detail="Page progress not found"
        )
    return page

@router.get("/progress/{crawler_id}/summary", response_model=CrawlerProgressSummary)
async def get_crawler_summary( # Added async
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    crawler_service: CrawlerService = Depends()
):
    """
    Get summary of crawler progress.
    """
    crawler = await crawler_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )

    return await crawler_service.get_summary(crawler_id)
