from pydantic import BaseModel, Field


class TicketRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1, max_length=5000)
    source: str = Field(default="chat", max_length=40)


class TicketResponse(BaseModel):
    reference_id: str
    status: str
