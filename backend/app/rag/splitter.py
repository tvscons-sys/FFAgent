"""Format-aware chunking policy for narrative and structured source documents."""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(documents: list[Document], chunk_size: int, chunk_overlap: int) -> list[Document]:
	chunks: list[Document] = []
	for document in documents:
		document_type = document.metadata.get("document_type")
		if document_type in {"spreadsheet", "presentation"}:
			chunks.append(document)
		elif document_type in {"pdf", "docx", "txt", "md"}:
			chunks.extend(split_narrative_document(document, chunk_size, chunk_overlap))
		else:
			raise ValueError(f"No chunking rule for document type: {document_type}")
	return chunks


def split_narrative_document(document: Document, chunk_size: int, chunk_overlap: int) -> list[Document]:
	"""Split one PDF/DOCX/text page or source unit while preserving its metadata."""
	splitter = RecursiveCharacterTextSplitter(
		chunk_size=chunk_size,
		chunk_overlap=chunk_overlap,
		separators=["\n## ", "\n# ", "\n\n", "\n", ". ", " ", ""],
		add_start_index=True,
	)
	chunks = splitter.split_documents([document])
	for chunk in chunks:
		chunk.metadata["chunk_strategy"] = "hybrid_text"
	return chunks