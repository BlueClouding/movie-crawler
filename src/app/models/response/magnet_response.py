
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MagnetResponse(BaseModel):
    movie_id: int
    url: str
    name: Optional[str] = None
    size: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class DownloadUrlResponse(BaseModel):
    id: int
    movie_id: int
    url: str
    source: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


    
class MagnetResponse(BaseModel):
    id: int
    movie_id: int
    link: str
    name: Optional[str] = None
    size: Optional[str] = None
    share_date: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
