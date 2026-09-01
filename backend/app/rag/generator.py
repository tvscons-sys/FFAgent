"""Grounded answer generation using Gemini and retrieved document chunks."""

from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.rag.retriever import SearchResult, semantic_search


GENERIC_FOLLOW_UP_TOKENS = {
    "help",
    "issue",
    "problem",
    "vehicle",
    "truck",
    "car",
    "works",
    "not working",
    "something",
    "please",
    "my",
}

SPECIFIC_CONTEXT_TOKENS = {
    "dtc",
    "fault",
    "code",
    "warning",
    "battery",
    "engine",
    "electrical",
    "brake",
    "sensor",
    "ac",
    "hvac",
    "oil",
    "fuel",
    "suspension",
    "airbag",
    "door",
    "lock",
    "starter",
    "charging",
    "overheating",
    "vibration",
    "noise",
    "monitor",
    "camera",
}


@dataclass(frozen=True)
class Answer:
	text: str
	sources: list[dict]


def needs_follow_up(query: str) -> bool:
	"""Return True when the user query is too vague to answer accurately."""
	if not query or not query.strip():
		return False

	text = query.strip().lower()
	words = text.split()
	if len(words) <= 4:
		return True

	icontains_specific_token = any(token in text for token in SPECIFIC_CONTEXT_TOKENS)
	icontains_generic_phrase = any(token in text for token in GENERIC_FOLLOW_UP_TOKENS)
	if icontains_specific_token and not icontains_generic_phrase:
		return False
	if icontains_specific_token and icontains_generic_phrase:
		return False
	return True


def build_follow_up_answer(query: str) -> str:
	"""Generate a short clarifying prompt for unresolved vague issues."""
	return (
		"I can help, but I need a bit more detail to give the right fix. "
		"Please tell me: 1) which vehicle / model / year, 2) the exact symptom or issue, "
		"and 3) any warning light, DTC code, or when it happens. "
		"If you share those details, I can narrow the likely cause and recommend the right next step."
	)


def answer_question(query: str) -> Answer:
	"""Retrieve relevant chunks and generate a grounded answer using Gemini."""
	retrieved = semantic_search(query, limit=settings.retrieval_top_k)
	return generate_answer_from_results(query, retrieved)


def generate_answer_from_results(query: str, retrieved: list[SearchResult]) -> Answer:
	"""Generate an answer from already-retrieved chunks without re-querying the vector store."""
	if not settings.google_api_key:
		raise ValueError("GOOGLE_API_KEY is not configured in .env")

	if not retrieved:
		return Answer(
			text="No relevant information found in the support documents.",
			sources=[],
		)

	context_text = _build_context(retrieved)
	answer_text = _generate_answer(query, context_text)
	sources = _extract_sources(retrieved)

	return Answer(text=answer_text, sources=sources)


def _build_context(results: list[SearchResult]) -> str:
	"""Format retrieved chunks into a context block for Gemini."""
	lines = []
	for index, result in enumerate(results, start=1):
		lines.append(f"[Source {index}]")
		lines.append(f"Document: {result.document.metadata.get('source')}")
		lines.append(f"Type: {result.document.metadata.get('document_type')}")
		
		location = (
			result.document.metadata.get("page_number")
			or result.document.metadata.get("slide_number")
			or result.document.metadata.get("row_number")
		)
		if location is not None:
			lines.append(f"Location: {location}")
		
		lines.append(f"Relevance: {result.relevance_score:.2%}")
		lines.append(f"Content:\n{result.document.page_content}\n")
	
	return "\n".join(lines)


def _generate_answer(query: str, context: str) -> str:
	"""Send the grounded prompt to Gemini and extract the answer."""
	client = ChatGoogleGenerativeAI(
		model=settings.gemini_model,
		api_key=settings.google_api_key,
	)
	
	system_prompt = SystemMessage(
		content=(
			"You are a helpful support assistant for FF vehicles. "
			"Answer the user's question using ONLY the provided context from support documents. "
			"If the information is not in the context, say so clearly. "
			"Be concise and practical. "
			"Include relevant part numbers, steps, or procedures when available."
		)
	)
	
	user_prompt = HumanMessage(
		content=f"Context from support documents:\n\n{context}\n\nQuestion: {query}"
	)
	
	response = client.invoke([system_prompt, user_prompt])
	return response.content.strip()


def _extract_sources(results: list[SearchResult]) -> list[dict]:
	"""Extract source metadata for citation."""
	sources = []
	for result in results:
		source_info = {
			"document": result.document.metadata.get("source"),
			"type": result.document.metadata.get("document_type"),
			"relevance": result.relevance_score,
		}
		
		location = (
			result.document.metadata.get("page_number")
			or result.document.metadata.get("slide_number")
			or result.document.metadata.get("row_number")
		)
		if location is not None:
			source_info["location"] = location
		
		sources.append(source_info)
	
	return sources
