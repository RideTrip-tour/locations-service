from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "location-service"
    debug: bool = False

    db_host: str = Field(
        validation_alias="DB_LOCATION_SERVICE_HOST", default="postgres"
    )
    db_port: int = Field(validation_alias="DB_LOCATION_SERVICE_PORT", default=5432)
    db_name: str = Field(
        validation_alias="DB_LOCATION_SERVICE_NAME", default="location_db"
    )
    db_user: str = Field(validation_alias="DB_LOCATION_SERVICE_USER", default="user")
    db_pass: str = Field(
        validation_alias="DB_LOCATION_SERVICE_PASS", default="password123"
    )
    db_driver: str = "postgresql+asyncpg"
    test_db_name: str = Field(
        validation_alias="TEST_DB_LOCATION_SERVICE_NAME", default="location_db_test"
    )

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.db_driver}://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def TEST_DATABASE_URL(self) -> str:
        return (
            f"{self.db_driver}://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.test_db_name}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        secrets_dir="/run/secrets",
    )


settings = Settings()
