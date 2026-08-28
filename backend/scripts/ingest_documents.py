"""Index source documents into the local ChromaDB collection."""

from pathlib import Path

from app.core.config import settings
from app.rag.embeddings import create_embeddings
from app.rag.loaders import load_source_documents
from app.rag.splitter import split_documents
from app.rag.vector_store import create_vector_store


def main() -> None:
	data_dir = Path(settings.data_dir)
	if not data_dir.is_absolute():
		data_dir = Path(__file__).resolve().parents[1] / data_dir
	source_documents = load_source_documents(data_dir)
	chunks = split_documents(source_documents, settings.chunk_size, settings.chunk_overlap)
	create_vector_store(
		chunks,
		create_embeddings(),
		settings.chroma_persist_directory,
		settings.chroma_collection,
	)
	print(f"Indexed {len(source_documents)} source documents into {len(chunks)} chunks.")


if __name__ == "__main__":
	main()