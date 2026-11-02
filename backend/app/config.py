import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    APP_NAME: str = "ReLoop"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "reloop-super-secure-production-ready-jwt-key-9988776655")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Database URL: defaults to local SQLite for instant zero-dependency execution,
    # or connects automatically to PostgreSQL / Supabase if DATABASE_URL is set in environment.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./reloop.db")
    
    # Recommendation Engine Configurable Default Weights
    # Financial: 35%, Useful Life: 30%, Convenience: 15%, Reuse: 20%
    WEIGHT_FINANCIAL: float = 0.35
    WEIGHT_USEFUL_LIFE: float = 0.30
    WEIGHT_CONVENIENCE: float = 0.15
    WEIGHT_REUSE: float = 0.20

settings = Settings()
