"""Core crawler components"""

from common.db.entity.base import DBBaseModel
from common.db.entity.movie import Movie
from common.db.entity.movie_info import MovieTitle
from common.db.entity.actress import Actress, ActressName
from common.db.entity.genre import Genre, GenreName
from common.db.entity.download import Magnet, DownloadUrl, WatchUrl
from common.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from common.enums.enums import SupportedLanguage