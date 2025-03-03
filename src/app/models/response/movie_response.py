from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, ConfigDict, Field

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

class GenrePair(BaseModel):
    genre: GenreResponse
    name: str
    
    @classmethod
    def from_tuple(cls, data: Tuple):
        genre, genre_name = data
        return cls(genre=genre, name=genre_name.name)

class ActressPair(BaseModel):
    actress: ActressResponse
    name: str
    
    @classmethod
    def from_tuple(cls, data: Tuple):
        actress, actress_name = data
        return cls(actress=actress, name=actress_name.name)

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
    titles: List[MovieTitleResponse] = Field(default_factory=list)
    actresses: List[ActressResponse] = Field(default_factory=list)
    genres: List[GenreResponse] = Field(default_factory=list)
    magnets: List[MagnetResponse] = Field(default_factory=list)
    download_urls: List[DownloadUrlResponse] = Field(default_factory=list)
    watch_urls: List[WatchUrlResponse] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate(cls, obj: Dict[str, Any]) -> "MovieDetailResponse":
        if isinstance(obj, dict):
            # 处理从字典创建的情况
            movie = obj.get("movie", {})
            
            # 处理标题数据
            titles_data = obj.get("titles", [])
            titles = []
            for title_data in titles_data:
                if isinstance(title_data, dict):
                    # 已经是字典格式
                    titles.append(MovieTitleResponse(**title_data))
                else:
                    # 如果是ORM对象
                    titles.append(MovieTitleResponse.model_validate(title_data))
            
            # 处理演员数据
            actresses_data = obj.get("actresses", [])
            actresses = []
            for actress_data in actresses_data:
                if isinstance(actress_data, dict):
                    # 已经是字典格式
                    actress = ActressResponse(
                        id=actress_data.get('actress_id'),
                        name=actress_data.get('name')
                    )
                    actresses.append(actress)
                else:
                    # 如果是ORM对象或元组
                    actress, _ = actress_data if isinstance(actress_data, tuple) else (actress_data, None)
                    actresses.append(ActressResponse.model_validate(actress))
            
            # 处理类型数据
            genres_data = obj.get("genres", [])
            genres = []
            for genre_data in genres_data:
                if isinstance(genre_data, dict):
                    # 已经是字典格式
                    genre = GenreResponse(
                        id=genre_data.get('genre_id'),
                        name=genre_data.get('name'),
                        urls=genre_data.get('urls', [])
                    )
                    genres.append(genre)
                else:
                    # 如果是ORM对象或元组
                    genre, _ = genre_data if isinstance(genre_data, tuple) else (genre_data, None)
                    genres.append(GenreResponse.model_validate(genre))
            
            # 处理磁力链接数据
            magnets_data = obj.get("magnets", [])
            magnets = []
            for magnet_data in magnets_data:
                if isinstance(magnet_data, dict):
                    # 已经是字典格式
                    magnets.append(MagnetResponse(**magnet_data))
                else:
                    # 如果是ORM对象
                    magnets.append(MagnetResponse.model_validate(magnet_data))
            
            # 处理下载链接数据
            download_urls_data = obj.get("download_urls", [])
            download_urls = []
            for url_data in download_urls_data:
                if isinstance(url_data, dict):
                    # 已经是字典格式
                    download_urls.append(DownloadUrlResponse(**url_data))
                else:
                    # 如果是ORM对象
                    download_urls.append(DownloadUrlResponse.model_validate(url_data))
            
            # 处理观看链接数据
            watch_urls_data = obj.get("watch_urls", [])
            watch_urls = []
            for url_data in watch_urls_data:
                if isinstance(url_data, dict):
                    # 已经是字典格式
                    watch_urls.append(WatchUrlResponse(**url_data))
                else:
                    # 如果是ORM对象
                    watch_urls.append(WatchUrlResponse.model_validate(url_data))
            
            return cls(
                id=movie.id,
                code=movie.code,
                duration=movie.duration,
                release_date=movie.release_date,
                cover_image_url=getattr(movie, "cover_image_url", None),
                preview_video_url=getattr(movie, "preview_video_url", None),
                likes=movie.likes,
                link=getattr(movie, "link", None),
                original_id=getattr(movie, "original_id", None),
                titles=titles,
                actresses=actresses,
                genres=genres,
                magnets=magnets,
                download_urls=download_urls,
                watch_urls=watch_urls
            )
        else:
            # 处理从ORM对象创建的情况
            return super().model_validate(obj)

