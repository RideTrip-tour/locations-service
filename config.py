from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    APP_NAME: str = "locations-service"
    DEBUG: bool = False

    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "location_db"))
    db_user: str = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres"))
    db_pass: str = os.getenv("DB_PASS", os.getenv("POSTGRES_PASSWORD", "postgres"))
    db_driver: str = "postgresql+asyncpg"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
