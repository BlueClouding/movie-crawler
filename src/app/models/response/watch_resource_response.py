from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WatchUrlResponse(BaseModel):
    id: int
    movie_id: int
    url: str
    source: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)