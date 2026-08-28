"""Hybrid chunking policy for narrative and structured source documents."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(documents: list[Document], chunk_size: int, chunk_overlap: int) -> list[Document]:
	text_documents = [document for document in documents if "chunk_strategy" not in document.metadata]
	structured_documents = [document for document in documents if "chunk_strategy" in document.metadata]
	splitter = RecursiveCharacterTextSplitter(
		chunk_size=chunk_size,
		chunk_overlap=chunk_overlap,
		separators=["\n## ", "\n# ", "\n\n", "\n", ". ", " ", ""],
		add_start_index=True,
	)
	chunks = splitter.split_documents(text_documents)
	for chunk in chunks:
		chunk.metadata["chunk_strategy"] = "hybrid_text"
	return chunks + structured_documents