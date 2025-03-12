from enum import Enum
from pydantic import BaseModel
from typing import Literal
from common.enums.enums import SupportedLanguage

class Start(str, Enum):
    GENRES = "genres"
    GENRES_PAGES = "genres_pages"
    MOVIES = "movies"
    ACTRESSES = "actresses"

class CrawlerRequest(BaseModel):
    base_url: str = "https://123av.com"
    language: SupportedLanguage = SupportedLanguage.JAPANESE
    threads: int = 3
    clear_existing: bool = False
    clear_all_data: bool = False
    output_dir: str = None
    # ENUM genres, movies, actresses
    start: Start = Start.GENRES