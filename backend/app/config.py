import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Link Shortener"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BASE_URL: str = "https://lk.kasunc.uk"
    
    # Database
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "linkshortener"
    MYSQL_PASSWORD: str = "your_secure_password"
    MYSQL_DATABASE: str = "linkshortener"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # Link Settings
    DEFAULT_CODE_LENGTH: int = 7
    MIN_CUSTOM_CODE_LENGTH: int = 3
    MAX_CUSTOM_CODE_LENGTH: int = 20
    DEFAULT_EXPIRY_DAYS: int = 30
    MAX_EXPIRY_DAYS: int = 365
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = 30
    RATE_LIMIT_BURST: int = 5
    
    # Reserved codes that cannot be used
    RESERVED_CODES: list = [
        "api", "admin", "www", "static", "assets", "health",
        "robots.txt", "favicon.ico", "sitemap.xml"
    ]
    
    class Config:
        # Resolve backend/.env relative to this file so settings load correctly
        env_file = str(Path(__file__).resolve().parents[1] / ".env")
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
