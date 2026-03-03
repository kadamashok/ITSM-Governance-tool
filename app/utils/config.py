from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ITSM Governance API"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8050
    log_level: str = "INFO"
    app_cors_origins: str = "http://localhost:5178,http://127.0.0.1:5178"

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "itsm_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None
    servicenow_instance_url: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""
    servicenow_oauth_redirect_uri: str = "http://127.0.0.1:8050/auth/callback"
    frontend_base_url: str = "http://127.0.0.1:5178"
    servicenow_timeout_seconds: int = 30
    servicenow_page_size: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.app_cors_origins.strip():
            return []
        return [item.strip() for item in self.app_cors_origins.split(",") if item.strip()]

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
