import secrets
from math import isfinite
from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "ReLoop"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60 * 24 * 7, gt=0)
    
    # Database URL: defaults to local SQLite for instant zero-dependency execution,
    # or connects automatically to PostgreSQL / Supabase if DATABASE_URL is set in environment.
    DATABASE_URL: str = "sqlite:///./reloop.db"
    CORS_ORIGINS: str = "http://localhost:3000"
    BOOTSTRAP_ADMIN_EMAIL: Optional[str] = None
    BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = None
    
    # Recommendation Engine Configurable Default Weights
    # Financial: 35%, Useful Life: 30%, Convenience: 15%, Reuse: 20%
    WEIGHT_FINANCIAL: float = 0.35
    WEIGHT_USEFUL_LIFE: float = 0.30
    WEIGHT_CONVENIENCE: float = 0.15
    WEIGHT_REUSE: float = 0.20

    @model_validator(mode="after")
    def validate_security_settings(self):
        if not self.SECRET_KEY:
            if self.APP_ENV.lower() == "production":
                raise ValueError("SECRET_KEY must be configured in production.")
            self.SECRET_KEY = secrets.token_urlsafe(48)
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters.")
        if bool(self.BOOTSTRAP_ADMIN_EMAIL) != bool(self.BOOTSTRAP_ADMIN_PASSWORD):
            raise ValueError("Set both bootstrap admin email and password, or neither.")
        if self.BOOTSTRAP_ADMIN_PASSWORD and not 12 <= len(self.BOOTSTRAP_ADMIN_PASSWORD) <= 72:
            raise ValueError("Bootstrap admin password must contain between 12 and 72 characters.")
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("Configure explicit trusted origins in CORS_ORIGINS; wildcards are not allowed.")
        weights = (
            self.WEIGHT_FINANCIAL,
            self.WEIGHT_USEFUL_LIFE,
            self.WEIGHT_CONVENIENCE,
            self.WEIGHT_REUSE,
        )
        if any(not isfinite(weight) or weight < 0 or weight > 1 for weight in weights):
            raise ValueError("Each recommendation weight must be a finite value between 0 and 1.")
        if abs(sum(weights) - 1.0) > 0.001:
            raise ValueError("Recommendation weights must sum to 1.0.")
        return self

settings = Settings()
