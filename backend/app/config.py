"""Application configuration loaded from environment variables (see backend/.env.example)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017/?directConnection=true"
    mongodb_db_name: str = "crate_scan_dev"

    # Firebase
    firebase_project_id: str = "demo-cratescan"
    firebase_service_account_json: str | None = None  # full JSON contents (server-only secret)
    firebase_auth_emulator_host: str | None = None  # local development / tests only
    super_admin_email: str | None = None

    # HTTP
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_upload_mb: int = 12
    max_json_kb: int = 1024
    rate_limit_default: str = "240/minute"
    rate_limit_ai: str = "12/minute"
    rate_limit_write: str = "60/minute"

    # AI providers
    ai_provider_order: str = "gemini,nvidia,huggingface"
    ai_timeout_seconds: float = 60.0
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_max_request_mb: float = 19.0
    nvidia_api_key: str | None = None
    nvidia_model: str = "meta/llama-3.2-90b-vision-instruct"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_max_image_kb: int = 180
    hf_api_key: str | None = None
    hf_model: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    hf_base_url: str = "https://router.huggingface.co/v1"
    hf_max_image_kb: int = 4096
    ocr_enabled: bool = False

    # Defaults for admin-editable settings (stored in the `settings` collection)
    ai_daily_limit_per_user: int = Field(default=60, ge=1, le=10000)
    photo_retention_days: int = Field(default=7, ge=1, le=90)

    @field_validator("super_admin_email")
    @classmethod
    def _lower(cls, v: str | None) -> str | None:
        return v.strip().lower() if v else v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def provider_order(self) -> list[str]:
        return [p.strip().lower() for p in self.ai_provider_order.split(",") if p.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
