from pydantic import BaseModel


class MovieTitleCreate(BaseModel):
    __allow_unmapped__ = True
    
    movie_id: int
    language_id: int
    title: str