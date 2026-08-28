from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FF AI Support Assistant API"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    data_dir: Path = Path("../data")
    chroma_persist_directory: Path = Path("./storage/chroma")
    chroma_collection: str = "ff_support_documents"
    hf_embedding_model: str = "BAAI/bge-small-en-v1.5"
    hf_embedding_device: str = "cpu"
    hf_normalize_embeddings: bool = True
    hf_embedding_dimension: int = 384
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 4
    rag_score_threshold: float = 0.55
    rag_request_timeout_seconds: float = 5.0
    supported_document_extensions: str = ".pdf,.docx,.txt,.md,.xlsx,.xlsm,.pptx"
    excel_row_as_chunk: bool = True
    excel_include_headers: bool = True
    pdf_chunk_strategy: str = "hybrid"
    pdf_chunk_size: int = 800
    pdf_chunk_overlap: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()