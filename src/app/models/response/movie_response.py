

from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.response.actress_response import ActressResponse
from app.models.response.genre_response import GenreResponse
from app.models.response.magnet_response import DownloadUrlResponse, MagnetResponse
from app.models.response.movie_info_response import MovieTitleResponse
from app.models.response.watch_resource_response import WatchUrlResponse


class MovieResponse(BaseModel):
    __allow_unmapped__ = True
    
    id: int
    code: str
    duration: Optional[str] = None
    release_date: Optional[str] = None
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: int
    link: Optional[str] = None
    original_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class MovieDetailResponse(BaseModel):
    id: int
    code: str
    duration: str
    release_date: str
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: int
    link: Optional[str] = None
    original_id: Optional[int] = None
    titles: List[MovieTitleResponse] = []
    actresses: List[ActressResponse] = []
    genres: List[GenreResponse] = []
    magnets: List[MagnetResponse] = []
    download_urls: List[DownloadUrlResponse] = []
    watch_url: List[WatchUrlResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

