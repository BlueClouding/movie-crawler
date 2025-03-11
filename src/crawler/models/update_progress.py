from pydantic import BaseModel
from typing import Optional

class GenrePageProgressUpdate(BaseModel):
        page: Optional[int] = None
        total_pages: Optional[int] = None
        code: Optional[str] = None
        status: Optional[str] = None
        total_items: Optional[int] = None