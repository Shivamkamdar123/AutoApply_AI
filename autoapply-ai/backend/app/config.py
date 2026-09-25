"""
Configuration & Environment Settings
====================================
Validates all required environment variables at startup using Pydantic Settings.
Fails fast with clear descriptive messages if required values are invalid.
"""

from pathlib import Path
from typing import List, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    """
    Central settings for the AutoApply AI agent.
    Values can be overridden via environment variables or a .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # CORS origins
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Matching Threshold & Algorithm Configuration
    MATCH_THRESHOLD: float = Field(default=0.35, ge=0.0, le=1.0)
    SIMILARITY_ENGINE: Literal["tfidf", "embedding"] = "tfidf"

    # Human-In-The-Loop Safety Valve: Defaults to safe dry-run mode
    # Auto-submit is NEVER the default and must be explicitly opted into.
    DRY_RUN: bool = True
    AUTO_SUBMIT_ENABLED: bool = False

    # Rate Limiting & Scraping Safety
    SCRAPE_DELAY_SECONDS: float = Field(default=2.0, ge=0.5)
    SCRAPER_USER_AGENT: str = "AutoApplyAI-Bot/1.0 (+https://github.com/Shivamkamdar123/AutoApply_AI)"
    MAX_SCRAPE_RESULTS: int = Field(default=25, ge=1, le=100)

    # Security & Storage
    SECRET_KEY: str = Field(
        default="autoapply-dev-secret-key-32bytes-for-aes!!",
        min_length=16,
        description="Master encryption key for local credentials storage"
    )
    DATABASE_PATH: Path = DATA_DIR / "autoapply.db"
    SCREENSHOTS_DIR: Path = DATA_DIR / "screenshots"
    FIXTURES_DIR: Path = DATA_DIR / "fixtures"

    SAMPLE_JOBS_FILE: Path = DATA_DIR / "sample_jobs.json"

    @field_validator("MATCH_THRESHOLD")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"MATCH_THRESHOLD must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v]
        return ["http://localhost:5500", "http://127.0.0.1:5500"]


# Instantiate settings singleton at startup to fail-fast if validation fails
settings = Settings()

# Ensure required directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
settings.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# Backward-compatibility aliases for existing imports
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS
MATCH_THRESHOLD = settings.MATCH_THRESHOLD
SAMPLE_JOBS_FILE = settings.SAMPLE_JOBS_FILE
