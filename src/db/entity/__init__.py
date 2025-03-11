"""Core crawler components"""

from src.db.entity.base import DBBaseModel
from app.db.entity.movie import Movie
from app.db.entity.movie_info import MovieTitle
from app.db.entity.actress import Actress, ActressName
from app.db.entity.genre import Genre, GenreName
from app.db.entity.download import Magnet, DownloadUrl, WatchUrl
from app.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from app.db.entity.enums import SupportedLanguage