from fastapi import FastAPI
from app.api.router import api_router
from app.config import settings

app = FastAPI(
    title="Movie Database API",
    description="API for managing movie database",
    version="1.0.0",
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Movie Database API. Go to /docs for documentation."}