"""
Configuration & Environment Settings
====================================
Validates all required environment variables at startup using Pydantic Settings.
Fails fast with clear descriptive messages if required values are invalid.
"""

from pathlib import Path
from typing import List, Literal, Optional
from pydantic import Field
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
    # NOTE: kept as a plain string field (not List[str]) on purpose.
    # Newer pydantic-settings versions try to JSON-decode any list-typed
    # field read from the environment/.env BEFORE any field_validator runs,
    # which breaks a simple comma-separated value like:
    #   ALLOWED_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
    # Reading it as a string and exposing the parsed list via a property
    # avoids that entirely and keeps .env.example's format working forever.
    ALLOWED_ORIGINS_RAW: str = Field(
        default="http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000",
        alias="ALLOWED_ORIGINS",
        description="Comma-separated list of frontend origins allowed to call this API.",
    )

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
    JWT_SECRET: str = Field(
        default="autoapply-dev-jwt-secret-key-do-not-use-in-production-32b!",
        min_length=16,
        description="Signing secret for JWT authentication tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Optional LLM integration (Anthropic Claude)
    ANTHROPIC_API_KEY: Optional[str] = None

    # Uploads & Limits
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB

    # Storage paths
    DATABASE_PATH: Path = DATA_DIR / "autoapply.db"
    SCREENSHOTS_DIR: Path = DATA_DIR / "screenshots"
    FIXTURES_DIR: Path = DATA_DIR / "fixtures"
    RESUMES_DIR: Path = DATA_DIR / "resumes"

    SAMPLE_JOBS_FILE: Path = DATA_DIR / "sample_jobs.json"

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parsed, trimmed list of allowed CORS origins from ALLOWED_ORIGINS_RAW."""
        if not self.ALLOWED_ORIGINS_RAW:
            return ["http://localhost:5500", "http://127.0.0.1:5500"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

    def model_post_init(self, __context: object) -> None:
        """Enforce production security constraints and fail fast if dev secrets are used."""
        if self.ENV == "production":
            if "dev-secret" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError("In production, SECRET_KEY must be a secure, random string of at least 32 characters.")
            if "dev-jwt" in self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                raise ValueError("In production, JWT_SECRET must be a secure, random string of at least 32 characters.")


# Instantiate settings singleton at startup to fail-fast if validation fails
settings = Settings()

# Ensure required directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
settings.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
settings.RESUMES_DIR.mkdir(parents=True, exist_ok=True)

# Backward-compatibility aliases for existing imports
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS
MATCH_THRESHOLD = settings.MATCH_THRESHOLD
SAMPLE_JOBS_FILE = settings.SAMPLE_JOBS_FILE