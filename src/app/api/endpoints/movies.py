from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from app.api.deps import get_services
from app.models.movie import MovieResponse, MovieDetailResponse
from app.models.enums import SupportedLanguage
from app.services import ServiceFactory
from app.models.download import DownloadUrlResponse, MagnetResponse, WatchUrlResponse

router = APIRouter()

@router.get("/", response_model=List[MovieResponse])
async def get_movies(
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve movies.
    """
    return await services.movie_service.get_all(skip=skip, limit=limit)

@router.get("/search/", response_model=List[MovieResponse])
async def search_movies(
    title: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search movies by title.
    """
    return await services.movie_service.search_by_title(
        title=title,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/recent/", response_model=List[MovieResponse])
async def get_recent_movies(
    days: int = Query(30, ge=1, le=365),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get recently released movies.
    """
    return await services.movie_service.get_recent_releases(
        days=days,
        skip=skip,
        limit=limit
    )

@router.get("/popular/", response_model=List[MovieResponse])
async def get_popular_movies(
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get popular movies based on likes.
    """
    return await services.movie_service.get_popular_movies(
        skip=skip,
        limit=limit
    )

@router.get("/{movie_code}", response_model=MovieDetailResponse)
async def get_movie_by_code(
    movie_code: str = Path(..., title="The code of the movie to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get movie by code.
    """
    movie = await services.movie_service.get_by_code(movie_code)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.post("/{movie_id}/like", response_model=MovieResponse)
async def like_movie(
    movie_id: int = Path(..., title="The ID of the movie to like"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Increment movie likes.
    """
    movie = await services.movie_service.increment_likes(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.get("/{movie_id}/magnets", response_model=List[MagnetResponse])
async def get_movie_magnets(
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all magnets for a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.magnet_service.get_by_movie_id(movie_id)

@router.get("/{movie_id}/download-urls", response_model=List[DownloadUrlResponse])
async def get_movie_download_urls(
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all download URLs for a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.download_url_service.get_by_movie_id(movie_id)

@router.get("/{movie_id}/watch-urls", response_model=List[WatchUrlResponse])
async def get_movie_watch_urls(
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all watch URLs for a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.watch_url_service.get_by_movie_id(movie_id)