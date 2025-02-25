"""Core crawler components"""

from database.models.base import BaseModel
from database.models.movie import Movie, MovieTitle
from database.models.actress import Actress, ActressName
from database.models.genre import Genre, GenreName
from database.models.download import Magnet, DownloadUrl, WatchUrl
from database.models.crawler import CrawlerProgress, PagesProgress, VideoProgress