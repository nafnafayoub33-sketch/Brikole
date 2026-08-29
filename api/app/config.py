"""Settings, read once from the environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SECRET = "dev-only-insecure-key-change-me"

#: Where the router is mounted. The refresh cookie is scoped relative to
#: this, so the two can never drift apart.
API_PREFIX = "/api/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    env: str = "development"

    database_url: str = "mysql+pymysql://brikole:devpassword@127.0.0.1:3306/brikole?charset=utf8mb4"
    secret_key: str = PLACEHOLDER_SECRET

    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_token_days: int = Field(default=30, ge=1, le=365)

    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    upload_dir: str = "var/uploads"

    sql_echo: bool = False

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url")
    @classmethod
    def _must_be_mysql(cls, value: str) -> str:
        if not value.startswith("mysql"):
            raise ValueError("DATABASE_URL must be a MySQL URL — this project targets MySQL 8")
        return value

    @model_validator(mode="after")
    def _refuse_placeholder_secret_in_production(self) -> Settings:
        # Shipping the example key would let anyone mint an admin token.
        if self.is_production and self.secret_key == PLACEHOLDER_SECRET:
            raise ValueError("SECRET_KEY is still the placeholder — set a real one in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
