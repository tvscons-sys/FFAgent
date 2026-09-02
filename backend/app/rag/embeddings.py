"""Local Hugging Face embedding provider."""

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings

# Global cache for embedding model (keeps it in memory)
_embeddings_cache: HuggingFaceEmbeddings | None = None


def create_embeddings() -> HuggingFaceEmbeddings:
	"""Get cached embeddings model or create it once."""
	global _embeddings_cache
	if _embeddings_cache is None:
		print("🚀 Initializing embedding model (first request, will cache)...")
		_embeddings_cache = HuggingFaceEmbeddings(
			model_name=settings.hf_embedding_model,
			model_kwargs={"device": settings.hf_embedding_device},
			encode_kwargs={"normalize_embeddings": settings.hf_normalize_embeddings},
		)
	return _embeddings_cache