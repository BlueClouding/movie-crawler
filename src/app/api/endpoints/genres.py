from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_services
from app.schemas.genre import (
    GenreCreate, GenreUpdate, GenreResponse, 
    GenreDetailResponse, GenreNameCreate
)
from app.schemas.movie import MovieResponse
from app.models.enums import SupportedLanguage
from app.services import ServiceFactory

router = APIRouter()

@router.get("/", response_model=List[GenreResponse])
def get_genres(
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve genres.
    """
    return services.genre_service.get_all(skip=skip, limit=limit)

@router.post("/", response_model=GenreResponse)
def create_genre(
    genre_in: GenreCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create new genre.
    """
    return services.genre_service.create(genre_in.dict())

@router.get("/{genre_id}", response_model=GenreDetailResponse)
def get_genre(
    genre_id: int = Path(..., title="The ID of the genre to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get genre by ID.
    """
    genre = services.genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return genre

@router.put("/{genre_id}", response_model=GenreResponse)
def update_genre(
    genre_in: GenreUpdate,
    genre_id: int = Path(..., title="The ID of the genre to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update genre.
    """
    genre = services.genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return services.genre_service.update(genre_id, genre_in.dict(exclude_unset=True))

@router.delete("/{genre_id}", response_model=bool)
def delete_genre(
    genre_id: int = Path(..., title="The ID of the genre to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Delete genre.
    """
    genre = services.genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return services.genre_service.delete(genre_id)

@router.post("/{genre_id}/names", response_model=GenreDetailResponse)
def add_genre_name(
    name_in: GenreNameCreate,
    genre_id: int = Path(..., title="The ID of the genre"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Add a name to a genre.
    """
    genre = services.genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    
    services.genre_service.add_name(
        genre_id=genre_id,
        name=name_in.name,
        language=name_in.language
    )
    
    return services.genre_service.get_by_id(genre_id)

@router.get("/search/", response_model=List[GenreResponse])
def search_genres(
    name: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search genres by name.
    """
    return services.genre_service.search_by_name(
        name=name,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/{genre_id}/movies", response_model=List[MovieResponse])
def get_genre_movies(
    genre_id: int = Path(..., title="The ID of the genre"),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all movies for a genre.
    """
    genre = services.genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return services.genre_service.get_movies_by_genre(
        genre_id=genre_id,
        skip=skip,
        limit=limit
    )