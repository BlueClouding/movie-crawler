from fastapi import APIRouter
from app.api.endpoints import movies, actresses, genres, crawler

api_router = APIRouter()

api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(actresses.router, prefix="/actresses", tags=["actresses"])
api_router.include_router(genres.router, prefix="/genres", tags=["genres"])
api_router.include_router(crawler.router, prefix="/crawler", tags=["crawler"])