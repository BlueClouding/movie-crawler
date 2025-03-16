"""Core crawler components"""

# Import base first to avoid circular imports
from common.db.entity.base import DBBaseModel, Base

# Only expose what's needed to avoid circular imports
__all__ = [
    'DBBaseModel', 'Base', 'Movie', 'MovieTitle', 'Actress', 'ActressName',
    'Genre', 'GenreName', 'Magnet', 'DownloadUrl', 'WatchUrl',
    'CrawlerProgress', 'PagesProgress', 'VideoProgress', 'SupportedLanguage'
]

# Lazy imports to avoid circular dependencies
from common.db.entity.movie import Movie
from common.db.entity.movie_info import MovieTitle
from common.db.entity.actress import Actress, ActressName
from common.db.entity.genre import Genre, GenreName
from common.db.entity.download import Magnet, DownloadUrl, WatchUrl
from common.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from common.enums.enums import SupportedLanguage