
from pydantic import BaseModel, ConfigDict


class MovieTitleResponse(BaseModel):
    movie_id: int
    language: str
    title: str
    id: int
    
    model_config = ConfigDict(from_attributes=True)
