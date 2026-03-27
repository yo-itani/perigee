from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "perigee"
    debug: bool = False

    # Slack
    slack_webhook_url: str | None = None
    slack_enabled: bool = True
    slack_http_timeout: int = 10

    # Web Server
    cors_origins: str = ""
    trusted_hosts: str = ""

    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "perigee"
    db_password: str = ""
    db_name: str = "perigee"

    model_config = SettingsConfigDict(env_prefix="PERIGEE_", env_file=".env")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def get_trusted_hosts(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]


settings = Settings()
