from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: str = "development"
    app_name: str = "FamilyCut API"
    secret_key: str = "change-me-to-a-32-char-secret-key"
    access_token_expire_minutes: int = 5_256_000
    refresh_token_expire_days: int = 3_650
    database_url: str = "sqlite:///./data/familycut.db"
    media_root: Path = Path("./data/media")
    report_image_root: Path = Path("./data/reports")
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    newapi_base_url: str | None = "http://localhost:23550/v1"
    newapi_api_key: str | None = None
    newapi_vision_model: str = "gemini-3-flash-preview"
    newapi_proxy_enabled: bool = False
    newapi_proxy_url: str | None = None

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "1099040334"
    bootstrap_admin_display_name: str = "家庭管理员"
    enforce_global_unique_username: bool = False
    default_activity_factor: float = 1.2
    default_goal_deficit_kcal: int = 500
    default_report_generate_hour: int = 23
    default_report_push_hour: int = 10

    report_template_title: str = Field(default="今日减脂日报")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_connect_args(self) -> dict[str, bool]:
        if self.database_url.startswith("sqlite"):
            return {"check_same_thread": False}
        return {}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.media_root.mkdir(parents=True, exist_ok=True)
    settings.report_image_root.mkdir(parents=True, exist_ok=True)
    return settings
