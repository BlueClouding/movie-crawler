from fastapi import APIRouter
from app.api.endpoints import movies, actresses, genres

api_router = APIRouter()

api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(actresses.router, prefix="/actresses", tags=["actresses"])
api_router.include_router(genres.router, prefix="/genres", tags=["genres"])
