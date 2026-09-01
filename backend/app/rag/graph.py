"""LangGraph workflow for grounded support answers."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
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


def _retrieve_documents(state: ChatState) -> dict[str, Any]:
    """Run semantic retrieval and store the ranked context."""
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
    }


def _generate_response(state: ChatState) -> dict[str, Any]:
    """Generate a grounded answer from the retrieved chunks."""
    result = generate_answer_from_results(state["query"], state["retrieved"])
    return {
        "answer": result.text,
        "sources": result.sources,
        "retrieved_count": len(result.sources),
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
    if clean_query.lower() in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        return {
            "answer": build_greeting_answer(),
            "sources": [],
            "retrieved_count": 0,
        }

    result = chat_graph.invoke({"query": clean_query})
    return {
        "answer": result.get("answer", "No relevant information found in the support documents."),
        "sources": result.get("sources", []),
        "retrieved_count": int(result.get("retrieved_count", 0)),
    }