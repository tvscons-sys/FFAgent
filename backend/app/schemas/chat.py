from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question to answer")


class ChatSource(BaseModel):
    document: str | None = None
    type: str | None = None
    location: str | int | None = None
    relevance: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = []
    retrieved_count: int = 0
