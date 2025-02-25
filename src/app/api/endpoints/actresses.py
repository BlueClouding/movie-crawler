from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_services
from app.schemas.actress import (
    ActressCreate, ActressUpdate, ActressResponse, 
    ActressDetailResponse, ActressNameCreate
)
from app.schemas.movie import MovieResponse
from app.models.enums import SupportedLanguage
from app.services import ServiceFactory

router = APIRouter()

@router.get("/", response_model=List[ActressResponse])
def get_actresses(
    skip: int = 0,
    limit: int = 100,
    services: ServiceFactory = Depends(get_services)
):
    """
    Retrieve actresses.
    """
    return services.actress_service.get_all(skip=skip, limit=limit)

@router.post("/", response_model=ActressResponse)
def create_actress(
    actress_in: ActressCreate,
    services: ServiceFactory = Depends(get_services)
):
    """
    Create new actress.
    """
    return services.actress_service.create(actress_in.dict())

@router.get("/{actress_id}", response_model=ActressDetailResponse)
def get_actress(
    actress_id: int = Path(..., title="The ID of the actress to get"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Get actress by ID.
    """
    actress = services.actress_service.get_by_id(actress_id)
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return actress

@router.put("/{actress_id}", response_model=ActressResponse)
def update_actress(
    actress_in: ActressUpdate,
    actress_id: int = Path(..., title="The ID of the actress to update"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Update actress.
    """
    actress = services.actress_service.get_by_id(actress_id)
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return services.actress_service.update(actress_id, actress_in.dict(exclude_unset=True))

@router.delete("/{actress_id}", response_model=bool)
def delete_actress(
    actress_id: int = Path(..., title="The ID of the actress to delete"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Delete actress.
    """
    actress = services.actress_service.get_by_id(actress_id)
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return services.actress_service.delete(actress_id)

@router.post("/{actress_id}/names", response_model=ActressDetailResponse)
def add_actress_name(
    name_in: ActressNameCreate,
    actress_id: int = Path(..., title="The ID of the actress"),
    services: ServiceFactory = Depends(get_services)
):
    """
    Add a name to an actress.
    """
    actress = services.actress_service.get_by_id(actress_id)
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    
    services.actress_service.add_name(
        actress_id=actress_id,
        name=name_in.name,
        language=name_in.language
    )
    
    return services.actress_service.get_by_id(actress_id)

@router.get("/search/", response_model=List[ActressResponse])
def search_actresses(
    name: str = Query(..., min_length=1),
    language: Optional[SupportedLanguage] = None,
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Search actresses by name.
    """
    return services.actress_service.search_by_name(
        name=name,
        language=language,
        skip=skip,
        limit=limit
    )

@router.get("/{actress_id}/movies", response_model=List[MovieResponse])
def get_actress_movies(
    actress_id: int = Path(..., title="The ID of the actress"),
    skip: int = 0,
    limit: int = 20,
    services: ServiceFactory = Depends(get_services)
):
    """
    Get all movies for an actress.
    """
    actress = services.actress_service.get_by_id(actress_id)
    if not actress:
        raise HTTPException(
            status_code=404,
            detail="Actress not found"
        )
    return services.actress_service.get_movies_by_actress(
        actress_id=actress_id,
        skip=skip,
        limit=limit
    )