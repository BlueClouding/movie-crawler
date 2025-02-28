from typing import Optional
from pydantic import BaseModel


class MovieCreate(BaseModel):
    __allow_unmapped__ = True

    code: str
    duration: str
    release_date: str
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: int = 0
    link: Optional[str] = None
    original_id: Optional[int] = None
    
class MovieUpdate(BaseModel):
    __allow_unmapped__ = True
    
    code: Optional[str] = None
    duration: Optional[str] = None
    release_date: Optional[str] = None
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: Optional[int] = None
    link: Optional[str] = None
    original_id: Optional[int] = None