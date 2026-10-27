from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    project_name: str = "CalorieTracker"
    api_v1_prefix: str = "/api"
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'calorie_tracker.db').as_posix()}"
    gemini_api_key: str = ""
    cors_origins: list[str] = ["*"]
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
