from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    # GHL OAuth Settings
    GHL_CLIENT_ID: str = Field(..., description="GHL OAuth Client ID")
    GHL_CLIENT_SECRET: str = Field(..., description="GHL OAuth Client Secret")
    GHL_REDIRECT_URI: str = Field(..., description="GHL OAuth Redirect URI")
    
    # Database Settings
    SUPABASE_DB_URL: str = Field(..., description="Database URL")
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging Level")
    
    @validator("GHL_CLIENT_ID")
    def validate_client_id(cls, v):
        if not v:
            raise ValueError("GHL_CLIENT_ID is required")
        return v
        
    @validator("GHL_CLIENT_SECRET")
    def validate_client_secret(cls, v):
        if not v:
            raise ValueError("GHL_CLIENT_SECRET is required")
        return v
        
    @validator("GHL_REDIRECT_URI")
    def validate_redirect_uri(cls, v):
        if not v:
            raise ValueError("GHL_REDIRECT_URI is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("GHL_REDIRECT_URI must be a valid URL")
        return v
        
    @validator("SUPABASE_DB_URL")
    def validate_db_url(cls, v):
        if not v:
            raise ValueError("SUPABASE_DB_URL is required")
        # Accept both PostgreSQL and Railway internal URLs
        if not (v.startswith("postgresql://") or v.startswith("${{ Postgres.postgres.railway.internal}}")):
            raise ValueError("SUPABASE_DB_URL must be a valid database connection string")
        return v
        
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings() 