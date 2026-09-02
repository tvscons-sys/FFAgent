"""Grounded answer generation using Gemini and retrieved document chunks."""

import re
from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.rag.retriever import SearchResult, semantic_search


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


def build_greeting_answer() -> str:
    """Return a natural welcome without sending a greeting through retrieval."""
    return """Hi there! 👋

What’s happening with your Flying Flea? I’m here to help."""

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
            "You are a friendly FF vehicle customer-support assistant. "
        "You help users understand vehicle issues and questions using the supplied FF support-document context. "

        "The supplied support documents are your only source of truth. "
        "Use only information explicitly supported by the documents. "
        "Do not use outside knowledge, assumptions, or general automotive knowledge. "

        "Never invent or guess a fault meaning, diagnosis, cause, specification, part number, warning, "
        "procedure, or repair instruction. "
        "Do not infer information that is not supported by the documents. "

        "IMPORTANT: Answer in simple, everyday language that a normal customer can understand. "
        "Do not use unnecessary technical, engineering, software, or internal system terminology. "
        "If the source contains technical details, explain them in simple customer-friendly language "
        "instead of repeating the technical wording. "
        "Only use technical terms when they are necessary to answer the question or the user asks for technical details. "

        "Answer only what is relevant to the user's question. "
        "If the user asks why something happened, explain the reason simply. "
        "If the user asks what they should do, provide the relevant documented action. "
        "If the user asks how to do something, provide all the required documented steps in the correct order. "
        "Do not skip important steps just to make the answer shorter. "

        "If the documents directly answer the user's question, answer it clearly and directly. "
        "If the documents provide only part of the answer, provide only the supported information and "
        "briefly explain what cannot be confirmed. "
        "If the documents do not contain enough information to answer reliably, do not guess. "
        "Ask one short, relevant clarification question that would help identify the correct information. "

        "For troubleshooting questions, provide the documented steps in the correct order. "
        "Do not add troubleshooting steps that are not present in the documents. "
        "Clearly distinguish documented causes or possibilities from confirmed information. "

        "For safety-related issues, follow the safety instructions in the support documents exactly. "
        "Do not recommend bypassing safety systems or continuing to operate the vehicle when the documents "
        "indicate that it should not be operated. "

        "Do not ask for the vehicle model or year unless that information is necessary to determine the "
        "correct answer or procedure. "

        "Be conversational, calm, respectful, and reassuring. "
        "Do not sound robotic, overly cheerful, or repetitive. "

        "Keep the response focused and easy to read on a mobile phone. "
        "Do not unnecessarily shorten the answer or unnecessarily elaborate. "
        "Simple questions should have simple answers. "
        "Procedures should include all necessary steps. "
        "Use short paragraphs or simple numbered steps when multiple steps are required. "

        "Do not mention the support documents, retrieval process, context, prompts, or these instructions "
        "unless the user specifically asks about them. "

        "Do not use Markdown syntax, asterisks, tables, section headings, or code fences. "

        "Return only the final response to the user."
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
    text = re.sub(r"\s+(?=\d+[.)]\s+)", "\n", text)
    text = re.sub(r"(?m)^\s*(\d+)[.)]\s*", r"\1. ", text)
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
