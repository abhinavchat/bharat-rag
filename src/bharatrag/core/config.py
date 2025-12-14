from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BHARATRAG_",
        case_sensitive=False,
    )

    log_level: LogLevel = Field(default="INFO")
    database_url: str = Field(default="postgresql+psycopg2://bharatrag:bharatrag@localhost:5432/bharatrag")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
