from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Server settings
    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 18080
    DEBUG: bool = False
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/movie_crawler"
    
    # Crawler settings
    BASE_URL: str = "http://123av.com"
    DEFAULT_LANGUAGE: str = "ja"
    DEFAULT_THREADS: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create settings instance
settings = Settings()