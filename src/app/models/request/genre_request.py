from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class GenreNameCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    genre_id: Optional[int] = None
    language: str
    name: str

class GenreCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    urls: List[str] = []
    names: List[GenreNameCreate] = []

class GenreUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    urls: Optional[List[str]] = None
    names: Optional[List[GenreNameCreate]] = None
