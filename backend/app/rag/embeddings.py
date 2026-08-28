"""Local Hugging Face embedding provider."""

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings


def create_embeddings() -> HuggingFaceEmbeddings:
	return HuggingFaceEmbeddings(
		model_name=settings.hf_embedding_model,
		model_kwargs={"device": settings.hf_embedding_device},
		encode_kwargs={"normalize_embeddings": settings.hf_normalize_embeddings},
	)