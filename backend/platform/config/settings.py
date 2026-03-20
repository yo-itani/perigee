from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "perigee"
    debug: bool = False

    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "perigee"
    db_password: str = ""
    db_name: str = "perigee"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_prefix": "PERIGEE_"}


settings = Settings()
