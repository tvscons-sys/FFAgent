"""Persistent ChromaDB storage for embedded document chunks."""

import hashlib
from pathlib import Path

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


def create_vector_store(
	documents: list[Document],
	embeddings: Embeddings,
	persist_directory: Path,
	collection_name: str,
) -> Chroma:
	persist_directory.mkdir(parents=True, exist_ok=True)
	vector_store = Chroma(
		collection_name=collection_name,
		embedding_function=embeddings,
		persist_directory=str(persist_directory),
		client_settings=ChromaSettings(anonymized_telemetry=False),
	)
	if documents:
		ids = [_document_id(document) for document in documents]
		vector_store.add_documents(documents, ids=ids)
	return vector_store


def reset_collection(persist_directory: Path, collection_name: str) -> None:
	"""Delete one local Chroma collection before a deliberate full rebuild."""
	from chromadb import PersistentClient

	client = PersistentClient(
		path=str(persist_directory),
		settings=ChromaSettings(anonymized_telemetry=False),
	)
	try:
		client.delete_collection(collection_name)
	except Exception:
		pass


def _document_id(document: Document) -> str:
	"""Create a stable ID so re-ingesting a file updates its chunks instead of duplicating them."""
	metadata = "|".join(f"{key}={document.metadata[key]}" for key in sorted(document.metadata))
	value = f"{document.page_content}|{metadata}"
	return hashlib.sha256(value.encode("utf-8")).hexdigest()