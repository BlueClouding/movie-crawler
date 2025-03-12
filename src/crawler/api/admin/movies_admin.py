from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from app.api.deps import get_services
from app.models.request.movie_info_request import MovieTitleCreate
from app.models.request.movie_request import MovieCreate, MovieUpdate
from app.models.response.movie_response import MovieDetailResponse, MovieResponse
from app.services import ServiceFactory

router = APIRouter()

@router.get("/", response_model=List[MovieResponse])
async def admin_get_movies(
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Admin: Retrieve all movies.
    """
    return await services.movie_service.get_all(skip=skip, limit=limit)

@router.post("/", response_model=MovieResponse)
async def create_movie(
    movie_in: MovieCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Admin: Create new movie.
    """
    return await services.movie_service.create(movie_in.dict())

@router.get("/{movie_id}", response_model=MovieDetailResponse)
async def admin_get_movie_by_id(
    movie_id: int = Path(..., title="The ID of the movie to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Admin: Get movie by ID.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return movie

@router.put("/{movie_id}", response_model=MovieResponse)
async def update_movie(
    movie_in: MovieUpdate,
    movie_id: int = Path(..., title="The ID of the movie to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Admin: Update movie.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.movie_service.update(movie_id, movie_in.dict(exclude_unset=True))

@router.delete("/{movie_id}", response_model=bool)
async def delete_movie(
    movie_id: int = Path(..., title="The ID of the movie to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Admin: Delete movie.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )
    return await services.movie_service.delete(movie_id)

@router.post("/{movie_id}/titles", response_model=MovieDetailResponse)
async def add_movie_title(
    title_in: MovieTitleCreate,
    movie_id: int = Path(..., title="The ID of the movie"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Admin: Add a title to a movie.
    """
    movie = await services.movie_service.get_by_id(movie_id)
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    await services.movie_service.add_title(
        movie_id=movie_id,
        title=title_in.title,
        language=title_in.language
    )

    return await services.movie_service.get_by_id(movie_id)