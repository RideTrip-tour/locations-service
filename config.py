from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "locations-service"
    DEBUG: bool = False

    # Pydantic сам найдет переменную DB_HOST в окружении. 
    # Если не найдет, возьмет дефолтное "localhost".
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    
    # AliasChoices позволяет искать сначала DB_NAME, а если ее нет - POSTGRES_DB
    db_name: str = Field(
        default="location_db", 
        validation_alias=AliasChoices("DB_NAME", "POSTGRES_DB")
    )
    db_user: str = Field(
        default="postgres", 
        validation_alias=AliasChoices("DB_USER", "POSTGRES_USER")
    )
    db_pass: str = Field(
        default="postgres", 
        validation_alias=AliasChoices("DB_PASS", "POSTGRES_PASSWORD")
    )
    
    db_driver: str = "postgresql+asyncpg"

    # Конфигурация: говорим Pydantic читать файл .env, если он есть
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Игнорируем другие переменные в окружении, чтобы не было ошибок
    )

    @property
    def DATABASE_URL(self) -> str:
        return f"{self.db_driver}://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()