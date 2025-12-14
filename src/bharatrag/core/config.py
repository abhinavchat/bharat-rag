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
    
    # LLM Configuration (Local-only, no external APIs)
    llm_backend: Literal["extractive", "local"] = Field(
        default="local",
        description="LLM backend: 'extractive' (stub) or 'local' (Hugging Face model)"
    )
    
    # Local LLM settings
    llm_model_name: str = Field(
        default="microsoft/DialoGPT-small",
        description="Hugging Face model identifier for local LLM. Recommended: 'microsoft/DialoGPT-small' (better for RAG) or 'gpt2' (faster but lower quality)"
    )
    llm_device: Literal["cpu", "cuda"] = Field(
        default="cpu",
        description="Device to run LLM on (cpu or cuda)"
    )
    llm_max_length: int = Field(
        default=512,
        ge=1,
        le=2048,
        description="Maximum generation length for LLM"
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for text generation (0.0 = deterministic, higher = more creative)"
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
