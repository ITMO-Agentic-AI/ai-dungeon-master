from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    langsmith_api_key: str = ""
    langsmith_project: str = "ai-dungeon-master"

    custom_model_enabled: bool = False
    custom_model_base_url: str = "http://localhost:8000/v1"
    custom_model_api_key: str = ""
    custom_model_name: str = "qwen3-32b"

    model_name: str = "claude-sonnet-4-20250514"
    model_temperature: float = 0.7

    dnd_api_base_url: str = "https://www.dnd5eapi.co/api"

    data_path: str = "src/data/storage"
    logs_path: str = "src/data/storage/logs"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings()
