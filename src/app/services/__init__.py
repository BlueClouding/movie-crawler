from sqlalchemy.orm import Session
from .movie_service import MovieService
from .actress_service import ActressService
from .genre_service import GenreService
from .magnet_service import MagnetService
from .download_url_service import DownloadUrlService
from .watch_url_service import WatchUrlService
from .crawler_service import CrawlerProgressService, PagesProgressService, VideoProgressService

class ServiceFactory:
    """服务工厂类，用于创建和管理所有服务实例"""
    
    def __init__(self, db: Session):
        self.db = db
        self._movie_service = None
        self._actress_service = None
        self._genre_service = None
        self._magnet_service = None
        self._download_url_service = None
        self._watch_url_service = None
        self._crawler_progress_service = None
        self._pages_progress_service = None
        self._video_progress_service = None
    
    @property
    def movie_service(self) -> MovieService:
        if not self._movie_service:
            self._movie_service = MovieService(self.db)
        return self._movie_service
    
    @property
    def actress_service(self) -> ActressService:
        if not self._actress_service:
            self._actress_service = ActressService(self.db)
        return self._actress_service
    
    @property
    def genre_service(self) -> GenreService:
        if not self._genre_service:
            self._genre_service = GenreService(self.db)
        return self._genre_service
    
    @property
    def magnet_service(self) -> MagnetService:
        if not self._magnet_service:
            self._magnet_service = MagnetService(self.db)
        return self._magnet_service
    
    @property
    def download_url_service(self) -> DownloadUrlService:
        if not self._download_url_service:
            self._download_url_service = DownloadUrlService(self.db)
        return self._download_url_service
    
    @property
    def watch_url_service(self) -> WatchUrlService:
        if not self._watch_url_service:
            self._watch_url_service = WatchUrlService(self.db)
        return self._watch_url_service
    
    @property
    def crawler_progress_service(self) -> CrawlerProgressService:
        if not self._crawler_progress_service:
            self._crawler_progress_service = CrawlerProgressService(self.db)
        return self._crawler_progress_service
    
    @property
    def pages_progress_service(self) -> PagesProgressService:
        if not self._pages_progress_service:
            self._pages_progress_service = PagesProgressService(self.db)
        return self._pages_progress_service
    
    @property
    def video_progress_service(self) -> VideoProgressService:
        if not self._video_progress_service:
            self._video_progress_service = VideoProgressService(self.db)
        return self._video_progress_service