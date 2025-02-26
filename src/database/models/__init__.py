"""Core crawler components"""

from app.models.base import DBBaseModel
from app.models.movie import Movie, MovieTitle
from app.models.actress import Actress, ActressName
from app.models.genre import Genre, GenreName
from app.models.download import Magnet, DownloadUrl, WatchUrl
from app.models.crawler import CrawlerProgress, PagesProgress, VideoProgress