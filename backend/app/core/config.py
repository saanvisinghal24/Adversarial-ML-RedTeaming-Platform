"""Application settings. Everything env-driven; no secrets in code."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Single DATABASE_URL so swapping local Postgres -> Supabase/Railway is a one-line change.
    DATABASE_URL: str = "postgresql+psycopg://redteam:redteam@localhost:5432/redteam"

    JWT_SECRET: str = "dev-only-secret-do-not-ship"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    STORAGE_DIR: Path = Path("./storage")
    MAX_MODEL_SIZE_MB: int = 200
    ALLOWED_MODEL_SUFFIXES: tuple[str, ...] = (".pkl", ".onnx", ".pt")

    # A scan that runs longer than this is killed and marked failed (M2's container has its own
    # wrapper-enforced kill; this is the backend-side backstop so a job can never hang forever).
    SCAN_TIMEOUT_SECONDS: int = 600

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "dev"

    @property
    def max_model_size_bytes(self) -> int:
        return self.MAX_MODEL_SIZE_MB * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
