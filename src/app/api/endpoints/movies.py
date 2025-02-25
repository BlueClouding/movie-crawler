from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_services
from app.schemas.movie import (
    MovieCreate, MovieUpdate, MovieResponse, 
    MovieDetailResponse, MovieTitleCreate
)
from app.models.enums import SupportedLanguage
from app.services import ServiceFactory

router = APIRouter()

@router.get("/", response_model=List[MovieResponse])
def get_movies(
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve movies.
    """
    return services.movie_service.get_all(skip=skip, limit=limit)

@router.post("/", response_model=MovieResponse)
def create_movie(
    movie_in: MovieCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create new movie.
    """
    return services.movie_service.create(movie_in.dict())

@router.get("/{movie_id}", response_model=MovieDetailResponse)
def get_movie(
    movie_id: int = Path(..., title="The ID of the movie to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get movie by ID.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.put("/{movie_id}", response_model=MovieResponse)
def update_movie(
    movie_in: MovieUpdate,
    movie_id: int = Path(..., title="The ID of the movie to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update movie.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return services.movie_service.update(movie_id, movie_in.dict(exclude_unset=True))

@router.delete("/{movie_id}", response_model=bool)
def delete_movie(
    movie_id: int = Path(..., title="The ID of the movie to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Delete movie.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return services.movie_service.delete(movie_id)

@router.post("/{movie_id}/titles", response_model=MovieDetailResponse)
def add_movie_title(
    title_in: MovieTitleCreate,
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Add a title to a movie.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    
    services.movie_service.add_title(
        movie_id=movie_id,
        title=title_in.title,
        language=title_in.language
    )
    
    return services.movie_service.get_by_id(movie_id)

@router.get("/search/", response_model=List[MovieResponse])
def search_movies(
    title: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search movies by title.
    """
    return services.movie_service.search_by_title(
        title=title,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/recent/", response_model=List[MovieResponse])
def get_recent_movies(
    days: int = Query(30, ge=1, le=365),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get recently released movies.
    """
    return services.movie_service.get_recent_releases(
        days=days,
        skip=skip,
        limit=limit
    )

@router.get("/popular/", response_model=List[MovieResponse])
def get_popular_movies(
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get popular movies based on likes.
    """
    return services.movie_service.get_popular_movies(
        skip=skip,
        limit=limit
    )

@router.post("/{movie_id}/like", response_model=MovieResponse)
def like_movie(
    movie_id: int = Path(..., title="The ID of the movie to like"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Increment movie likes.
    """
    movie = services.movie_service.increment_likes(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.get("/{movie_id}/magnets", response_model=List[MagnetResponse])
def get_movie_magnets(
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all magnets for a movie.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return services.magnet_service.get_by_movie_id(movie_id)

@router.get("/{movie_id}/download-urls", response_model=List[DownloadUrlResponse])
def get_movie_download_urls(
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all download URLs for a movie.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return services.download_url_service.get_by_movie_id(movie_id)

@router.get("/{movie_id}/watch-urls", response_model=List[WatchUrlResponse])
def get_movie_watch_urls(
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all watch URLs for a movie.
    """
    movie = services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return services.watch_url_service.get_by_movie_id(movie_id)