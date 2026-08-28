"""Index source documents into the local ChromaDB collection."""

import argparse
from pathlib import Path

from app.core.config import settings
from app.rag.embeddings import create_embeddings
from app.rag.loaders import load_source_documents
from app.rag.splitter import split_documents
from app.rag.vector_store import create_vector_store, reset_collection


def main() -> None:
	parser = argparse.ArgumentParser(description="Index support documents into ChromaDB.")
	parser.add_argument(
		"--rebuild",
		action="store_true",
		help="Delete the configured Chroma collection before indexing all source files.",
	)
	args = parser.parse_args()

	data_dir = Path(settings.data_dir)
	if not data_dir.is_absolute():
		data_dir = Path(__file__).resolve().parents[1] / data_dir
	if args.rebuild:
		reset_collection(settings.chroma_persist_directory, settings.chroma_collection)
	source_documents = load_source_documents(data_dir)
	chunks = split_documents(source_documents, settings.chunk_size, settings.chunk_overlap)
	create_vector_store(
		chunks,
		create_embeddings(),
		settings.chroma_persist_directory,
		settings.chroma_collection,
	)
	mode = "rebuilt" if args.rebuild else "updated"
	print(f"Loaded {len(source_documents)} source units and {mode} {len(chunks)} chunks in ChromaDB.")


if __name__ == "__main__":
	main()