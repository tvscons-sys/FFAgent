from pydantic import BaseModel


class IngestionResponse(BaseModel):
    status: str
    documents: int
    chunks: int