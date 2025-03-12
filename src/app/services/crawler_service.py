from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from typing import List, Optional, Dict, Any
from datetime import datetime

from common.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from .base_service import BaseService

class CrawlerProgressService(BaseService[CrawlerProgress]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, CrawlerProgress)
    
    async def get_by_task_type(self, task_type: str) -> Optional[CrawlerProgress]:
        result = await self.db.execute(
            select(CrawlerProgress).filter(CrawlerProgress.task_type == task_type)
        )
        return result.scalars().first()
    
    async def update_status(self, crawler_id: int, status: str) -> Optional[CrawlerProgress]:
        crawler = await self.get(crawler_id)
        if not crawler:
            return None
        
        crawler.status = status
        crawler.last_update = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(crawler)
        return crawler
    
    async def get_active_tasks(self) -> List[CrawlerProgress]:
        result = await self.db.execute(
            select(CrawlerProgress).filter(CrawlerProgress.status.in_(['pending', 'running']))
        )
        return result.scalars().all()

class PagesProgressService(BaseService[PagesProgress]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, PagesProgress)
    
    async def get_by_crawler_id(self, crawler_id: int) -> List[PagesProgress]:
        result = await self.db.execute(
            select(PagesProgress)
            .filter(PagesProgress.crawler_progress_id == crawler_id)
            .order_by(PagesProgress.page_number)
        )
        return result.scalars().all()
    
    async def get_by_relation_and_type(self, relation_id: int, page_type: str) -> List[PagesProgress]:
        result = await self.db.execute(
            select(PagesProgress)
            .filter(PagesProgress.relation_id == relation_id, 
                   PagesProgress.page_type == page_type)
            .order_by(PagesProgress.page_number)
        )
        return result.scalars().all()
    
    async def update_progress(self, page_id: int, processed_items: int, status: str = None) -> Optional[PagesProgress]:
        page = await self.get(page_id)
        if not page:
            return None
        
        page.processed_items = processed_items
        if status:
            page.status = status
        
        page.last_update = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(page)
        return page
    
    async def get_pending_pages(self, limit: int = 10) -> List[PagesProgress]:
        result = await self.db.execute(
            select(PagesProgress)
            .filter(PagesProgress.status == 'pending')
            .order_by(PagesProgress.created_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_progress_summary(self, crawler_id: int) -> Dict[str, Any]:
        pages = await self.get_by_crawler_id(crawler_id)
        
        total_pages = len(pages)
        completed_pages = sum(1 for page in pages if page.status == 'completed')
        total_items = sum(page.total_items for page in pages)
        processed_items = sum(page.processed_items for page in pages)
        
        return {
            "total_pages": total_pages,
            "completed_pages": completed_pages,
            "total_items": total_items,
            "processed_items": processed_items,
            "completion_percentage": (processed_items / total_items * 100) if total_items > 0 else 0
        }

class VideoProgressService(BaseService[VideoProgress]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, VideoProgress)
    
    async def get_by_code(self, code: str) -> Optional[VideoProgress]:
        result = await self.db.execute(
            select(VideoProgress).filter(VideoProgress.code == code)
        )
        return result.scalars().first()
    
    async def get_by_genre_id(self, genre_id: int, skip: int = 0, limit: int = 100) -> List[VideoProgress]:
        result = await self.db.execute(
            select(VideoProgress)
            .filter(VideoProgress.genre_id == genre_id)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_pending_videos(self, limit: int = 20) -> List[VideoProgress]:
        result = await self.db.execute(
            select(VideoProgress)
            .filter(VideoProgress.status == 'pending')
            .order_by(VideoProgress.created_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_failed_videos(self, retry_limit: int = 3, limit: int = 20) -> List[VideoProgress]:
        result = await self.db.execute(
            select(VideoProgress)
            .filter(VideoProgress.status == 'failed', 
                   VideoProgress.retry_count < retry_limit)
            .order_by(VideoProgress.updated_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_status(self, video_id: int, status: str, error: str = None) -> Optional[VideoProgress]:
        video = await self.get(video_id)
        if not video:
            return None
        
        video.status = status
        if status == 'failed':
            video.retry_count += 1
            if error:
                video.last_error = error
        
        video.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(video)
        return video
    
    async def mark_detail_fetched(self, video_id: int) -> Optional[VideoProgress]:
        video = await self.get(video_id)
        if not video:
            return None
        
        video.detail_fetched = True
        video.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(video)
        return video
    
    async def get_stats_by_genre(self) -> List[Dict[str, Any]]:
        """获取每个类型的视频处理统计信息"""
        stmt = (
            select(
                VideoProgress.genre_id,
                func.count(VideoProgress.id).label('total'),
                func.sum(case([(VideoProgress.status == 'completed', 1)], else_=0)).label('completed'),
                func.sum(case([(VideoProgress.status == 'failed', 1)], else_=0)).label('failed'),
                func.sum(case([(VideoProgress.status == 'pending', 1)], else_=0)).label('pending')
            ).group_by(VideoProgress.genre_id)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "genre_id": row.genre_id,
                "total": row.total,
                "completed": row.completed,
                "failed": row.failed,
                "pending": row.pending,
                "completion_percentage": (row.completed / row.total * 100) if row.total > 0 else 0
            }
            for row in rows
        ]