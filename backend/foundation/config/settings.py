from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "perigee"
    debug: bool = False

    # Slack
    slack_webhook_url: str | None = None
    slack_enabled: bool = True
    slack_http_timeout: int = 10

    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "perigee"
    db_password: str = ""
    db_name: str = "perigee"

    # JWT / Auth
    jwt_secret_key: str = ""
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_prefix="PERIGEE_", env_file=".env")


settings = Settings()
