from functools import lru_cache
import math
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "CareerLens AI"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:5173"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "careerlens"
    db_user: str = "careerlens_user"
    db_password: SecretStr | None = None
    redis_url: str | None = None
    cors_allowed_origins: list[str] = Field(default_factory=list)
    celery_task_always_eager: bool = False
    secret_key: SecretStr
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    resume_storage_dir: Path = PROJECT_ROOT / "backend" / "var" / "private-resumes"
    resume_encryption_key: SecretStr | None = None
    resume_max_file_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    resume_max_pages: int = Field(default=100, ge=1, le=500)
    resume_max_extracted_chars: int = Field(default=1_000_000, ge=1000)
    skill_taxonomy_path: Path | None = None
    spacy_model: str = "en_core_web_sm"
    matching_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    matching_embedding_dimensions: Literal[384] = 384
    matching_max_search_candidates: int = Field(default=500, ge=10, le=5000)
    matching_skill_weight: float = Field(default=0.35, ge=0, le=1)
    matching_experience_weight: float = Field(default=0.30, ge=0, le=1)
    matching_semantic_weight: float = Field(default=0.25, ge=0, le=1)
    matching_education_weight: float = Field(default=0.10, ge=0, le=1)

    @model_validator(mode="after")
    def validate_matching_weights(self) -> "Settings":
        if not self.database_url:
            if self.db_password is None:
                raise ValueError("Set DATABASE_URL or DB_PASSWORD.")
            password = quote_plus(self.db_password.get_secret_value())
            self.database_url = (
                f"postgresql+psycopg://{quote_plus(self.db_user)}:{password}"
                f"@{self.db_host}:{self.db_port}/{quote_plus(self.db_name)}"
            )
        weights = (
            self.matching_skill_weight,
            self.matching_experience_weight,
            self.matching_semantic_weight,
            self.matching_education_weight,
        )
        if not math.isclose(sum(weights), 1.0, rel_tol=0, abs_tol=1e-6):
            raise ValueError("Matching component weights must sum to 1.")
        origins = self.cors_allowed_origins or [self.frontend_url]
        if "*" in origins:
            raise ValueError("CORS origins must not contain a wildcard.")
        if any(not origin.startswith(("http://", "https://")) for origin in origins):
            raise ValueError("CORS origins must be absolute HTTP(S) origins.")
        self.cors_allowed_origins = list(dict.fromkeys(origins))
        if self.app_env == "production":
            if (
                self.db_password is None
                or "replace_with" in self.db_password.get_secret_value().lower()
            ):
                raise ValueError("A generated DB_PASSWORD is required in production.")
            if self.redis_url is None:
                raise ValueError("REDIS_URL is required in production.")
            if self.resume_encryption_key is None:
                raise ValueError("RESUME_ENCRYPTION_KEY is required in production.")
        return self

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or "replace_with" in secret.lower():
            raise ValueError(
                "SECRET_KEY must be a generated secret of at least 32 characters."
            )
        return value

    @field_validator("resume_encryption_key", mode="before")
    @classmethod
    def normalize_empty_resume_key(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def normalize_empty_gemini_key(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_empty_redis_url(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("resume_encryption_key")
    @classmethod
    def validate_resume_encryption_key(
        cls, value: SecretStr | None
    ) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError(
                "RESUME_ENCRYPTION_KEY must be at least 32 characters when configured."
            )
        if value is not None and "replace_with" in value.get_secret_value().lower():
            raise ValueError("RESUME_ENCRYPTION_KEY must be generated.")
        return value

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
