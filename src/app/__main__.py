import uvicorn
from app import app
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )