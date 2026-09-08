"""LangGraph workflow for grounded support answers."""

from time import perf_counter
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.core.admin_metrics import record_chat
from app.rag.faq import FAQ_ITEMS, get_faq_suggestions, match_faq
from app.rag.generator import (
    build_greeting_answer,
    generate_answer_from_results,
)
from app.rag.retriever import SearchResult, semantic_search


class ChatState(TypedDict):
    query: str
    retrieved: list[SearchResult]
    answer: str
    sources: list[dict]
    retrieved_count: int
    retrieval_latency_ms: float


def _retrieve_documents(state: ChatState) -> dict[str, Any]:
    """Run semantic retrieval and store the ranked context."""
    started = perf_counter()
    results = semantic_search(state["query"], limit=settings.retrieval_top_k)
    return {
        "retrieved": results,
        "retrieved_count": len(results),
        "sources": [
            {
                "document": result.document.metadata.get("source"),
                "type": result.document.metadata.get("document_type"),
                "location": (
                    result.document.metadata.get("page_number")
                    or result.document.metadata.get("slide_number")
                    or result.document.metadata.get("row_number")
                ),
                "relevance": result.relevance_score,
            }
            for result in results
        ],
        "retrieval_latency_ms": round((perf_counter() - started) * 1000, 1),
    }


def _generate_response(state: ChatState) -> dict[str, Any]:
    """Generate a grounded answer from the retrieved chunks."""
    result = generate_answer_from_results(state["query"], state["retrieved"])
    return {
        "answer": result.text,
        "sources": result.sources,
        "retrieved_count": len(result.sources),
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "estimated_cost_inr": result.estimated_cost_inr,
    }


workflow = StateGraph(ChatState)
workflow.add_node("retrieve", _retrieve_documents)
workflow.add_node("generate", _generate_response)
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
chat_graph = workflow.compile()


def chat(query: str) -> dict[str, Any]:
    """Execute the retrieval -> generation workflow for one user question."""
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    clean_query = query.strip()
    suggestions = get_faq_suggestions()

    if clean_query.lower() in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        greeting = build_greeting_answer()
        record_chat({
            "query": clean_query,
            "answer": greeting,
            "model": "rule-based greeting",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_inr": 0,
            "latency_ms": 0,
            "retrieval_latency_ms": 0,
            "retrieved_count": 0,
            "sources": [],
        })
        return {
            "answer": greeting,
            "sources": [],
            "retrieved_count": -1,
            "suggestions": suggestions,
            "faq_match": False,
        }

    faq_match = match_faq(clean_query)
    if faq_match is not None:
        record_chat({
            "query": clean_query,
            "answer": faq_match["answer"],
            "model": "faq-rule",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_inr": 0,
            "latency_ms": 0,
            "retrieval_latency_ms": 0,
            "retrieved_count": 0,
            "sources": [],
        })
        return {
            "answer": faq_match["answer"],
            "sources": [],
            "retrieved_count": 0,
            "suggestions": suggestions,
            "faq_match": True,
        }

    started = perf_counter()
    result = chat_graph.invoke({"query": clean_query})
    response = {
        "answer": result.get("answer", "No relevant information found in the support documents."),
        "sources": result.get("sources", []),
        "retrieved_count": int(result.get("retrieved_count", 0)),
        "suggestions": suggestions,
        "faq_match": False,
    }
    input_tokens = int(result.get("input_tokens", 0))
    output_tokens = int(result.get("output_tokens", 0))
    # Some provider responses omit usage metadata; keep the admin row useful.
    if input_tokens == 0:
        input_tokens = max(1, len(clean_query) // 4)
    if output_tokens == 0:
        output_tokens = max(1, len(response["answer"]) // 4)
    record_chat({
        "query": clean_query,
        "answer": response["answer"],
        "model": result.get("model", settings.gemini_model),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost_inr": float(result.get("estimated_cost_inr", 0)),
        "latency_ms": round((perf_counter() - started) * 1000, 1),
        "retrieval_latency_ms": float(result.get("retrieval_latency_ms", 0)),
        "retrieved_count": response["retrieved_count"],
        "sources": response["sources"],
    })
    return response