from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_services
from app.schemas.crawler import (
    CrawlerProgressCreate, CrawlerProgressResponse, 
    PagesProgressCreate, PagesProgressResponse,
    VideoProgressCreate, VideoProgressResponse,
    CrawlerProgressSummary
)
from app.services import ServiceFactory

router = APIRouter()

@router.get("/progress", response_model=List[CrawlerProgressResponse])
def get_crawler_progress(
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all crawler progress records.
    """
    return services.crawler_progress_service.get_all()

@router.post("/progress", response_model=CrawlerProgressResponse)
def create_crawler_progress(
    crawler_in: CrawlerProgressCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create a new crawler progress record.
    """
    return services.crawler_progress_service.create(crawler_in.dict())

@router.get("/progress/{crawler_id}", response_model=CrawlerProgressResponse)
def get_crawler_progress_by_id(
    crawler_id: int = Path(..., title="The ID of the crawler progress to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get crawler progress by ID.
    """
    crawler = services.crawler_progress_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return crawler

@router.put("/progress/{crawler_id}/status", response_model=CrawlerProgressResponse)
def update_crawler_status(
    status: str = Query(..., title="New status"),
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update crawler progress status.
    """
    crawler = services.crawler_progress_service.update_status(crawler_id, status)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return crawler

@router.get("/progress/{crawler_id}/pages", response_model=List[PagesProgressResponse])
def get_pages_progress(
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all pages progress for a crawler.
    """
    crawler = services.crawler_progress_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    return services.pages_progress_service.get_by_crawler_id(crawler_id)

@router.post("/progress/{crawler_id}/pages", response_model=PagesProgressResponse)
def create_page_progress(
    page_in: PagesProgressCreate,
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Create a new page progress record.
    """
    crawler = services.crawler_progress_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    
    page_data = page_in.dict()
    page_data["crawler_progress_id"] = crawler_id
    
    return services.pages_progress_service.create(page_data)

@router.put("/pages/{page_id}/progress", response_model=PagesProgressResponse)
def update_page_progress(
    processed_items: int = Query(..., ge=0, title="Number of processed items"),
    status: str = Query(None, title="New status"),
    page_id: int = Path(..., title="The ID of the page progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update page progress.
    """
    page = services.pages_progress_service.update_progress(page_id, processed_items, status)
    if not page:
        raise HTTPException(
            status_code=404,
            detail="Page progress not found"
        )
    return page

@router.get("/progress/{crawler_id}/summary", response_model=CrawlerProgressSummary)
def get_crawler_summary(
    crawler_id: int = Path(..., title="The ID of the crawler progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get summary of crawler progress.
    """
    crawler = services.crawler_progress_service.get_by_id(crawler_id)
    if not crawler:
        raise HTTPException(
            status_code=404,
            detail="Crawler progress not found"
        )
    
    return services.pages_progress_service.get_progress_summary(crawler_id)

@router.get("/videos", response_model=List[VideoProgressResponse])
def get_video_progress(
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
        return services.video_progress_service.get_by_genre_id(genre_id, skip, limit)
    elif status == "pending":
        return services.video_progress_service.get_pending_videos(limit)
    elif status == "failed":
        return services.video_progress_service.get_failed_videos(limit=limit)
    else:
        return services.video_progress_service.get_all(skip, limit)

@router.post("/videos", response_model=VideoProgressResponse)
def create_video_progress(
    video_in: VideoProgressCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create a new video progress record.
    """
    return services.video_progress_service.create(video_in.dict())

@router.put("/videos/{video_id}/status", response_model=VideoProgressResponse)
def update_video_status(
    status: str = Query(..., title="New status"),
    error: str = Query(None, title="Error message"),
    video_id: int = Path(..., title="The ID of the video progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update video progress status.
    """
    video = services.video_progress_service.update_status(video_id, status, error)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video progress not found"
        )
    return video

@router.put("/videos/{video_id}/mark-fetched", response_model=VideoProgressResponse)
def mark_video_detail_fetched(
    video_id: int = Path(..., title="The ID of the video progress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Mark video details as fetched.
    """
    video = services.video_progress_service.mark_detail_fetched(video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video progress not found"
        )
    return video

@router.get("/videos/stats", response_model=List[Dict[str, Any]])
def get_video_stats(
    services: ServiceFactory = Depends(get_services)
):
    """
    Get video processing statistics by genre.
    """
    return services.video_progress_service.get_stats_by_genre()