"""
Application configuration using Pydantic Settings.
Supports loading from .env and system environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Aboo Perfume Sommelier API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8008

    # Paths
    catalog_json_path: str = "app/data/perfumes_catalog.json"
    database_path: str = "perfumes.db"

    # LLM Settings
    # Default is 'auto' (detects available key, falls back to intelligent Sommelier Mock if none set)
    llm_provider: str = Field(default="auto", description="LLM provider: 'auto', 'openai', 'anthropic', 'gemini', 'mock'")
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None

    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"

    # Catalog & Validation Settings
    validation_threshold: float = 72.0  # Fuzzy matching threshold (0-100)
    enforce_catalog_validation: bool = True  # Strict anti-hallucination verification

    # External APIs (optional, e.g., Scento API integration)
    scento_api_key: Optional[str] = None
    scento_api_url: str = "https://api.scento.app/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
