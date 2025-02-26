from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_services
from app.models.movie import (
    MovieCreate, MovieUpdate, MovieResponse,
    MovieDetailResponse, MovieTitleCreate
)
from app.models.enums import SupportedLanguage
from app.services import ServiceFactory
from app.models.download import DownloadUrlResponse, MagnetResponse, WatchUrlResponse

router = APIRouter()

@router.get("/", response_model=List[MovieResponse])
async def get_movies( # Added async
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve movies.
    """
    return await services.movie_service.get_all(skip=skip, limit=limit) # Added await

@router.post("/", response_model=MovieResponse)
async def create_movie( # Added async
    movie_in: MovieCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create new movie.
    """
    return await services.movie_service.create(movie_in.dict()) # Added await

@router.get("/{movie_id}", response_model=MovieDetailResponse)
async def get_movie( # Added async
    movie_id: int = Path(..., title="The ID of the movie to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get movie by ID.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.put("/{movie_id}", response_model=MovieResponse)
async def update_movie( # Added async
    movie_in: MovieUpdate,
    movie_id: int = Path(..., title="The ID of the movie to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update movie.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.movie_service.update(movie_id, movie_in.dict(exclude_unset=True)) # Added await

@router.delete("/{movie_id}", response_model=bool)
async def delete_movie( # Added async
    movie_id: int = Path(..., title="The ID of the movie to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Delete movie.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.movie_service.delete(movie_id) # Added await

@router.post("/{movie_id}/titles", response_model=MovieDetailResponse)
async def add_movie_title( # Added async
    title_in: MovieTitleCreate,
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Add a title to a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    await services.movie_service.add_title( # Added await
        movie_id=movie_id,
        title=title_in.title,
        language=title_in.language
    )

    return await services.movie_service.get_by_id(movie_id) # Added await

@router.get("/search/", response_model=List[MovieResponse])
async def search_movies( # Added async
    title: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search movies by title.
    """
    return await services.movie_service.search_by_title( # Added await
        title=title,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/recent/", response_model=List[MovieResponse])
async def get_recent_movies( # Added async
    days: int = Query(30, ge=1, le=365),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get recently released movies.
    """
    return await services.movie_service.get_recent_releases( # Added await
        days=days,
        skip=skip,
        limit=limit
    )

@router.get("/popular/", response_model=List[MovieResponse])
async def get_popular_movies( # Added async
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get popular movies based on likes.
    """
    return await services.movie_service.get_popular_movies( # Added await
        skip=skip,
        limit=limit
    )

@router.post("/{movie_id}/like", response_model=MovieResponse)
async def like_movie( # Added async
    movie_id: int = Path(..., title="The ID of the movie to like"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Increment movie likes.
    """
    movie = await services.movie_service.increment_likes(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.get("/{movie_id}/magnets", response_model=List[MagnetResponse])
async def get_movie_magnets( # Added async
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all magnets for a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.magnet_service.get_by_movie_id(movie_id) # Added await

@router.get("/{movie_id}/download-urls", response_model=List[DownloadUrlResponse])
async def get_movie_download_urls( # Added async
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all download URLs for a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.download_url_service.get_by_movie_id(movie_id) # Added await

@router.get("/{movie_id}/watch-urls", response_model=List[WatchUrlResponse])
async def get_movie_watch_urls( # Added async
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all watch URLs for a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id) # Added await
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.watch_url_service.get_by_movie_id(movie_id) # Added await