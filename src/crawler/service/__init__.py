from sqlalchemy.ext.asyncio import AsyncSession
from crawler.service.crawler_progress_service import CrawlerProgressService
from crawler.service.crawler_service import CrawlerService
from crawler.service.genre_service import GenreService
from crawler.service.genre_page_service import GenrePageService
from crawler.service.movie_detail_info import MovieDetailInfoService
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService

class ServiceFactory:
    """服务工厂类，用于创建和管理所有服务实例"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        self._crawler_progress_service = None
        self._crawler_service = None
        self._genre_service = None
        self._genre_page_service = None
        self._movie_detail_info_service = None
        self._movie_detail_crawler_service = None
        
    
    @property
    def crawler_progress_service(self) -> CrawlerProgressService:
        if not self._crawler_progress_service:
            self._crawler_progress_service = CrawlerProgressService(self.db)
        return self._crawler_progress_service
    
    @property
    def crawler_service(self) -> CrawlerService:
        if not self._crawler_service:
            self._crawler_service = CrawlerService(self.db)
        return self._crawler_service
    
    @property
    def genre_service(self) -> GenreService:
        if not self._genre_service:
            self._genre_service = GenreService(self.db)
        return self._genre_service
    
    @property
    def genre_page_service(self) -> GenrePageService:
        if not self._genre_page_service:
            self._genre_page_service = GenrePageService(self.db)    
        return self._genre_page_service
    
    @property
    def movie_detail_info_service(self) -> MovieDetailInfoService:
        if not self._movie_detail_info_service:
            self._movie_detail_info_service = MovieDetailInfoService(self.db)
        return self._movie_detail_info_service
    
    @property
    def movie_detail_crawler_service(self) -> MovieDetailCrawlerService:
        if not self._movie_detail_crawler_service:
            self._movie_detail_crawler_service = MovieDetailCrawlerService(self.db)
        return self._movie_detail_crawler_service