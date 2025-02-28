from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_services

from app.services import ServiceFactory
from db.entity.enums import SupportedLanguage
from models.request.genre_request import GenreCreate, GenreNameCreate, GenreUpdate
from models.response.genre_response import GenreDetailResponse, GenreResponse
from models.response.movie_response import MovieResponse

router = APIRouter()

@router.get("/", response_model=List[GenreResponse])
async def get_genres( # Added async
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve genres.
    """
    return await services.genre_service.get_all(skip=skip, limit=limit) # Added await

@router.post("/", response_model=GenreResponse)
async def create_genre( # Added async
    genre_in: GenreCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create new genre.
    """
    return await services.genre_service.create(genre_in.dict()) # Added await

@router.get("/{genre_id}", response_model=GenreDetailResponse)
async def get_genre( # Added async
    genre_id: int = Path(..., title="The ID of the genre to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get genre by ID.
    """
    genre = await services.genre_service.get_by_id(genre_id) # Added await
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return genre

@router.put("/{genre_id}", response_model=GenreResponse)
async def update_genre( # Added async
    genre_in: GenreUpdate,
    genre_id: int = Path(..., title="The ID of the genre to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update genre.
    """
    genre = await services.genre_service.get_by_id(genre_id) # Added await
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return await services.genre_service.update(genre_id, genre_in.dict(exclude_unset=True)) # Added await

@router.delete("/{genre_id}", response_model=bool)
async def delete_genre( # Added async
    genre_id: int = Path(..., title="The ID of the genre to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Delete genre.
    """
    genre = await services.genre_service.get_by_id(genre_id) # Added await
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return await services.genre_service.delete(genre_id) # Added await

@router.post("/{genre_id}/names", response_model=GenreDetailResponse)
async def add_genre_name( # Added async
    name_in: GenreNameCreate,
    genre_id: int = Path(..., title="The ID of the genre"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Add a name to a genre.
    """
    genre = await services.genre_service.get_by_id(genre_id) # Added await
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )

    await services.genre_service.add_name( # Added await
        genre_id=genre_id,
        name=name_in.name,
        language=name_in.language
    )

    return await services.genre_service.get_by_id(genre_id) # Added await

@router.get("/search/", response_model=List[GenreResponse])
async def search_genres( # Added async
    name: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search genres by name.
    """
    return await services.genre_service.search_by_name( # Added await
        name=name,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/{genre_id}/movies", response_model=List[MovieResponse])
async def get_genre_movies( # Added async
    genre_id: int = Path(..., title="The ID of the genre"),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all movies for a genre.
    """
    genre = await services.genre_service.get_by_id(genre_id) # Added await
    if not genre:
        raise HTTPException(
            status_code=404,
            detail="Genre not found"
        )
    return await services.genre_service.get_movies_by_genre( # Added await
        genre_id=genre_id,
        skip=skip,
        limit=limit
    )