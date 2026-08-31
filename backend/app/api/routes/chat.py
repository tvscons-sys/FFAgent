from fastapi import APIRouter

from app.rag.graph import chat
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Answer a user question using the retrieval and generation pipeline."""
    result = chat(request.query)

    return ChatResponse(
        answer=result["answer"],
        sources=[
            ChatSource(
                document=item.get("document"),
                type=item.get("type"),
                location=item.get("location"),
                relevance=item.get("relevance"),
            )
            for item in result.get("sources", [])
        ],
        retrieved_count=len(result.get("sources", [])),
    )
