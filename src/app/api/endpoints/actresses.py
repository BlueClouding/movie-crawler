from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_services
from app.db.entity.enums import SupportedLanguage
from app.models.request.actress_request import ActressCreate, ActressNameCreate, ActressUpdate
from app.models.response.actress_response import ActressDetailResponse, ActressResponse
from app.models.response.movie_response import MovieResponse
from app.services import ServiceFactory


router = APIRouter()

@router.get("/", response_model=List[ActressResponse])
async def get_actresses( # Added async
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve actresses.
    """
    return await services.actress_service.get_all(skip=skip, limit=limit) # Added await

@router.post("/", response_model=ActressResponse)
async def create_actress( # Added async
    actress_in: ActressCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create new actress.
    """
    return await services.actress_service.create(actress_in.dict()) # Added await

@router.get("/{actress_id}", response_model=ActressDetailResponse)
async def get_actress( # Added async
    actress_id: int = Path(..., title="The ID of the actress to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get actress by ID.
    """
    actress = await services.actress_service.get_by_id(actress_id) # Added await
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return actress

@router.put("/{actress_id}", response_model=ActressResponse)
async def update_actress( # Added async
    actress_in: ActressUpdate,
    actress_id: int = Path(..., title="The ID of the actress to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update actress.
    """
    actress = await services.actress_service.get_by_id(actress_id) # Added await
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return await services.actress_service.update(actress_id, actress_in.dict(exclude_unset=True)) # Added await

@router.delete("/{actress_id}", response_model=bool)
async def delete_actress( # Added async
    actress_id: int = Path(..., title="The ID of the actress to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Delete actress.
    """
    actress = await services.actress_service.get_by_id(actress_id) # Added await
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return await services.actress_service.delete(actress_id) # Added await

@router.post("/{actress_id}/names", response_model=ActressDetailResponse)
async def add_actress_name( # Added async
    name_in: ActressNameCreate,
    actress_id: int = Path(..., title="The ID of the actress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Add a name to an actress.
    """
    actress = await services.actress_service.get_by_id(actress_id) # Added await
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )

    await services.actress_service.add_name( # Added await
        actress_id=actress_id,
        name=name_in.name,
        language=name_in.language
    )

    return await services.actress_service.get_by_id(actress_id) # Added await

@router.get("/search/", response_model=List[ActressResponse])
async def search_actresses( # Added async
    name: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search actresses by name.
    """
    return await services.actress_service.search_by_name( # Added await
        name=name,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/{actress_id}/movies", response_model=List[MovieResponse])
async def get_actress_movies( # Added async
    actress_id: int = Path(..., title="The ID of the actress"),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all movies for an actress.
    """
    actress = await services.actress_service.get_by_id(actress_id) # Added await
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return await services.actress_service.get_movies_by_actress( # Added await
        actress_id=actress_id,
        skip=skip,
        limit=limit
    )