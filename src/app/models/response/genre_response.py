
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

class GenreNameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    genre_id: int
    language: str
    name: str
    created_at: datetime

class GenreResponse(BaseModel):
    id: int
    urls: Optional[List[str]] = None
    names: List[GenreNameResponse] = []
    model_config = ConfigDict(from_attributes=True)

class GenreDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    urls: List[str]
    created_at: datetime
    names: List[GenreNameResponse] = []
    movies: List[dict] = []  # 或使用 MovieResponse 类型