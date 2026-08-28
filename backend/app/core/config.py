from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FF AI Support Assistant API"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    data_dir: Path = Path("../data")
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "ff_support_documents"
    embedding_model: str = "models/text-embedding-004"
    google_api_key: str = ""
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 4

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()