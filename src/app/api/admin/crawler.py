from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_services
from app.db.entity.crawler import (
    CrawlerProgressCreate,
    CrawlerProgressResponse, 
    PagesProgressCreate, PagesProgressResponse,
    VideoProgressCreate, VideoProgressResponse,
    CrawlerProgressSummary
)
from app.services import ServiceFactory

router = APIRouter()

@router.get("/progress", response_model=List[CrawlerProgressResponse])
async def get_crawler_progress( # Added async
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all crawler progress records.
    """
    return await services.crawler_progress_service.get_all() # Added await

@router.post("/progress", response_model=CrawlerProgressResponse)
async def create_crawler_progress( # Added async
    crawler_in: CrawlerProgressCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create a new crawler progress record.
    """
    return await services.crawler_progress_service.create(crawler_in.dict()) # Added await

@router.get("/progress/{crawler_id}", response_model=CrawlerProgressResponse)
async def get_crawler_progress_by_id( # Added async
    crawler_id: int = Path(..., title="The ID of the crawler progress to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get crawler progress by ID.
    """
    crawler = await services.crawler_progress_service.get_by_id(crawler_id) # Added await
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
    services: ServiceFactory = Depends(get_services)
):
    """
    Update crawler progress status.
    """
    crawler = await services.crawler_progress_service.update_status(crawler_id, status) # Added await
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return crawler

@router.get("/progress/{crawler_id}/pages", response_model=List[PagesProgressResponse])
async def get_pages_progress( # Added async
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all pages progress for a crawler.
    """
    crawler = await services.crawler_progress_service.get_by_id(crawler_id) # Added await
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return await services.pages_progress_service.get_by_crawler_id(crawler_id) # Added await

@router.post("/progress/{crawler_id}/pages", response_model=PagesProgressResponse)
async def create_page_progress( # Added async
    page_in: PagesProgressCreate,
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Create a new page progress record.
    """
    crawler = await services.crawler_progress_service.get_by_id(crawler_id) # Added await
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
    services: ServiceFactory = Depends(get_services)
):
    """
    Update page progress.
    """
    page = await services.pages_progress_service.update_progress(page_id, processed_items, status) # Added await
    if not page:
        raise HTTPException(
            status_code=404,
            detail="Page progress not found"
        )
    return page

@router.get("/progress/{crawler_id}/summary", response_model=CrawlerProgressSummary)
async def get_crawler_summary( # Added async
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get summary of crawler progress.
    """
    crawler = await services.crawler_progress_service.get_by_id(crawler_id) # Added await
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )

    return await services.pages_progress_service.get_progress_summary(crawler_id) # Added await

@router.get("/videos", response_model=List[VideoProgressResponse])
async def get_video_progress( # Added async
    status: str = Query(None, title="Filter by status"),
    genre_id: int = Query(None, title="Filter by genre ID"),
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get video progress records.
    """
    if genre_id:
        return await services.video_progress_service.get_by_genre_id(genre_id, skip, limit) # Added await
    elif status == "pending":
        return await services.video_progress_service.get_pending_videos(limit) # Added await
    elif status == "failed":
        return await services.video_progress_service.get_failed_videos(limit=limit) # Added await
    else:
        return await services.video_progress_service.get_all(skip, limit) # Added await

@router.post("/videos", response_model=VideoProgressResponse)
async def create_video_progress( # Added async
    video_in: VideoProgressCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create a new video progress record.
    """
    return await services.video_progress_service.create(video_in.dict()) # Added await

@router.put("/videos/{video_id}/status", response_model=VideoProgressResponse)
async def update_video_status( # Added async
    status: str = Query(..., title="New status"),
    error: str = Query(None, title="Error message"),
    video_id: int = Path(..., title="The ID of the video progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update video progress status.
    """
    video = await services.video_progress_service.update_status(video_id, status, error) # Added await
    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video progress not found"
        )
    return video

@router.put("/videos/{video_id}/mark-fetched", response_model=VideoProgressResponse)
async def mark_video_detail_fetched( # Added async
    video_id: int = Path(..., title="The ID of the video progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Mark video details as fetched.
    """
    video = await services.video_progress_service.mark_detail_fetched(video_id) # Added await
    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video progress not found"
        )
    return video

@router.get("/videos/stats", response_model=List[Dict[str, Any]])
async def get_video_stats( # Added async
    services: ServiceFactory = Depends(get_services)
):
    """
    Get video processing statistics by genre.
    """
    return await services.video_progress_service.get_stats_by_genre() # Added await