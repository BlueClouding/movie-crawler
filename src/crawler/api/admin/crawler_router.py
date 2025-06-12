import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel
from enum import Enum
from crawler.models.request.crawler_request import CrawlerRequest
from common.db.entity.crawler import (
    CrawlerProgress,
    CrawlerProgressCreate,
    CrawlerProgressResponse,
    PagesProgressCreate,
    PagesProgressResponse,
    CrawlerProgressSummary,
)
from crawler.service.crawler_service import CrawlerService


# 获取日志记录器
logger = logging.getLogger(__name__)


class Start(str, Enum):
    GENRES = "genres"
    GENRES_PAGES = "genres_pages"
    MOVIES = "movies"
    ACTRESSES = "actresses"


class CrawlerResponse(BaseModel):
    task_id: int
    status: str
    message: str


router = APIRouter()
