"""Persistent ChromaDB storage for embedded document chunks."""

from pathlib import Path

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
	existing = Chroma(
		collection_name=collection_name,
		embedding_function=embeddings,
		persist_directory=str(persist_directory),
	)
	try:
		existing.delete_collection()
	except Exception:
		pass
	vector_store = Chroma(
		collection_name=collection_name,
		embedding_function=embeddings,
		persist_directory=str(persist_directory),
	)
	if documents:
		vector_store.add_documents(documents)
	return vector_store