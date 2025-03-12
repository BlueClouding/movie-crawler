from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuration settings for the application, including server, database, and crawler settings."""

    # Server settings
    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 8001
    DEBUG: bool = False
    
    # Database settings
    # Using dqy superuser account to ensure we have proper permissions
    DATABASE_URL: str = "postgresql+asyncpg://dqy@localhost:5432/movie_crawler"
    
    # Crawler settings
    BASE_URL: str = "http://123av.com"
    DEFAULT_LANGUAGE: str = "ja"
    DEFAULT_THREADS: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create settings instance
settings = Settings()