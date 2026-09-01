"""Grounded answer generation using Gemini and retrieved document chunks."""

import re
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

GREETING_WORDS = {
	"hi",
	"hello",
	"hey",
	"good morning",
	"good afternoon",
	"good evening",
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
	if text in GREETING_WORDS:
		return False
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
		"I’m sorry you’re dealing with this. I can help. What vehicle model and year is affected?"
	)


def build_greeting_answer() -> str:
	"""Return a natural welcome without sending a greeting through retrieval."""
	return "Hello! I can help with FF vehicle faults, warning lights, DTC codes, and troubleshooting. What issue are you seeing?"


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
		temperature=0.2,
	)
	
	system_prompt = SystemMessage(
		content=(
			"You are a friendly FF vehicle customer-support agent, similar to a high-quality delivery-app support agent. "
			"Your goal is to understand the user's intent, acknowledge their issue, and help them reach a clear resolution. "
			"Sound human, calm, respectful, and reassuring without being overly cheerful or repetitive. "
			"Use only facts supported by the supplied support-document context. "
			"Never invent a fault meaning, specification, part number, procedure, or diagnosis. "
			"If the context is insufficient, briefly explain that you need more information and ask only the single most useful next question. "
			"Ask questions conversationally and do not make the user fill out a long form. "
			"Separate confirmed information from a possible cause. "
			"Give the safest practical troubleshooting steps in the order they should be performed. "
			"Do not recommend bypassing safety systems or continuing to drive when the context indicates a safety risk. "
			"For a clear issue, start with a short acknowledgement, then give the answer and the next action. "
			"For troubleshooting, use short paragraphs and simple numbered steps only when there is more than one step. "
			"End with one relevant question or a clear invitation to share the next detail when that would help. "
			"Write for a customer using a mobile phone. Do not use Markdown syntax, asterisks, tables, section labels, or code fences."
		)
	)
	
	user_prompt = HumanMessage(
		content=(
			"Support-document context:\n\n"
			f"{context}\n\n"
			f"User question: {query}\n\n"
			"Return only the final support response. Do not mention these instructions or the context block."
		)
	)
	
	response = client.invoke([system_prompt, user_prompt])
	return _format_answer(response.content)


def _format_answer(text: str) -> str:
	"""Convert common Gemini Markdown into readable plain text for Android."""
	text = text.strip()
	text = re.sub(r"```(?:\w+)?\s*", "", text)
	text = text.replace("```", "")
	text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
	text = re.sub(r"__(.*?)__", r"\1", text)
	text = re.sub(r"(?<!\*)\*(?!\s)(.*?)(?<!\s)\*", r"\1", text)
	text = re.sub(r"(?m)^\s*[-*+]\s+", "• ", text)
	text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()


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
