from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from models import CrawlerProgress, PagesProgress, VideoProgress
from .base_service import BaseService

class CrawlerProgressService(BaseService[CrawlerProgress]):
    def __init__(self, db: Session):
        super().__init__(db, CrawlerProgress)
    
    def get_by_task_type(self, task_type: str) -> Optional[CrawlerProgress]:
        return self.db.query(CrawlerProgress)\
            .filter(CrawlerProgress.task_type == task_type)\
            .first()
    
    def update_status(self, crawler_id: int, status: str) -> Optional[CrawlerProgress]:
        crawler = self.get_by_id(crawler_id)
        if not crawler:
            return None
        
        crawler.status = status
        crawler.last_update = datetime.utcnow()
        self.db.commit()
        self.db.refresh(crawler)
        return crawler
    
    def get_active_tasks(self) -> List[CrawlerProgress]:
        return self.db.query(CrawlerProgress)\
            .filter(CrawlerProgress.status.in_(['pending', 'running']))\
            .all()

class PagesProgressService(BaseService[PagesProgress]):
    def __init__(self, db: Session):
        super().__init__(db, PagesProgress)
    
    def get_by_crawler_id(self, crawler_id: int) -> List[PagesProgress]:
        return self.db.query(PagesProgress)\
            .filter(PagesProgress.crawler_progress_id == crawler_id)\
            .order_by(PagesProgress.page_number)\
            .all()
    
    def get_by_relation_and_type(self, relation_id: int, page_type: str) -> List[PagesProgress]:
        return self.db.query(PagesProgress)\
            .filter(PagesProgress.relation_id == relation_id, 
                   PagesProgress.page_type == page_type)\
            .order_by(PagesProgress.page_number)\
            .all()
    
    def update_progress(self, page_id: int, processed_items: int, status: str = None) -> Optional[PagesProgress]:
        page = self.get_by_id(page_id)
        if not page:
            return None
        
        page.processed_items = processed_items
        if status:
            page.status = status
        
        page.last_update = datetime.utcnow()
        self.db.commit()
        self.db.refresh(page)
        return page
    
    def get_pending_pages(self, limit: int = 10) -> List[PagesProgress]:
        return self.db.query(PagesProgress)\
            .filter(PagesProgress.status == 'pending')\
            .order_by(PagesProgress.created_at)\
            .limit(limit)\
            .all()
    
    def get_progress_summary(self, crawler_id: int) -> Dict[str, Any]:
        pages = self.get_by_crawler_id(crawler_id)
        
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
    def __init__(self, db: Session):
        super().__init__(db, VideoProgress)
    
    def get_by_code(self, code: str) -> Optional[VideoProgress]:
        return self.db.query(VideoProgress)\
            .filter(VideoProgress.code == code)\
            .first()
    
    def get_by_genre_id(self, genre_id: int, skip: int = 0, limit: int = 100) -> List[VideoProgress]:
        return self.db.query(VideoProgress)\
            .filter(VideoProgress.genre_id == genre_id)\
            .offset(skip).limit(limit)\
            .all()
    
    def get_pending_videos(self, limit: int = 20) -> List[VideoProgress]:
        return self.db.query(VideoProgress)\
            .filter(VideoProgress.status == 'pending')\
            .order_by(VideoProgress.created_at)\
            .limit(limit)\
            .all()
    
    def get_failed_videos(self, retry_limit: int = 3, limit: int = 20) -> List[VideoProgress]:
        return self.db.query(VideoProgress)\
            .filter(VideoProgress.status == 'failed', 
                   VideoProgress.retry_count < retry_limit)\
            .order_by(VideoProgress.updated_at)\
            .limit(limit)\
            .all()
    
    def update_status(self, video_id: int, status: str, error: str = None) -> Optional[VideoProgress]:
        video = self.get_by_id(video_id)
        if not video:
            return None
        
        video.status = status
        if status == 'failed':
            video.retry_count += 1
            if error:
                video.last_error = error
        
        video.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(video)
        return video
    
    def mark_detail_fetched(self, video_id: int) -> Optional[VideoProgress]:
        video = self.get_by_id(video_id)
        if not video:
            return None
        
        video.detail_fetched = True
        video.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(video)
        return video
    
    def get_stats_by_genre(self) -> List[Dict[str, Any]]:
        """获取每个类型的视频处理统计信息"""
        from sqlalchemy import func, case
        
        stats = self.db.query(
            VideoProgress.genre_id,
            func.count(VideoProgress.id).label('total'),
            func.sum(case([(VideoProgress.status == 'completed', 1)], else_=0)).label('completed'),
            func.sum(case([(VideoProgress.status == 'failed', 1)], else_=0)).label('failed'),
            func.sum(case([(VideoProgress.status == 'pending', 1)], else_=0)).label('pending')
        ).group_by(VideoProgress.genre_id).all()
        
        return [
            {
                "genre_id": row.genre_id,
                "total": row.total,
                "completed": row.completed,
                "failed": row.failed,
                "pending": row.pending,
                "completion_percentage": (row.completed / row.total * 100) if row.total > 0 else 0
            }
            for row in stats
        ]