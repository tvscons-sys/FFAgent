"""Semantic retrieval over the persisted ChromaDB collection."""

from dataclasses import dataclass
from pathlib import Path
import re

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embeddings import create_embeddings


@dataclass(frozen=True)
class SearchResult:
	document: Document
	relevance_score: float


def create_retriever() -> Chroma:
	"""Open the existing persisted Chroma collection without re-indexing it."""
	persist_directory = settings.chroma_persist_directory
	if not persist_directory.is_absolute():
		persist_directory = Path.cwd() / persist_directory
	return Chroma(
		collection_name=settings.chroma_collection,
		embedding_function=create_embeddings(),
		persist_directory=str(persist_directory),
		client_settings=ChromaSettings(anonymized_telemetry=False),
	)


def semantic_search(
	query: str,
	limit: int | None = None,
	minimum_score: float | None = None,
) -> list[SearchResult]:
	"""Return the most relevant chunks, filtering weak semantic matches."""
	clean_query = query.strip()
	if not clean_query:
		raise ValueError("Search query cannot be empty.")
	if limit is not None and limit < 1:
		raise ValueError("Search limit must be at least 1.")

	retriever = create_retriever()
	results = retriever.similarity_search_with_relevance_scores(
		clean_query,
		k=(limit or settings.retrieval_top_k) * 3,
	)
	threshold = settings.rag_score_threshold if minimum_score is None else minimum_score
	filtered = [
		SearchResult(document=document, relevance_score=score)
		for document, score in results
		if score >= threshold
	]
	query_terms = [term.lower() for term in re.findall(r"[a-z0-9]+", clean_query) if len(term) >= 3]
	filtered.sort(
		key=lambda result: (
			sum(term in result.document.page_content.lower() for term in query_terms),
			result.relevance_score,
		),
		reverse=True,
	)
	return filtered[: limit or settings.retrieval_top_k]