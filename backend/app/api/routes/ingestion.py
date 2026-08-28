from fastapi import APIRouter

from app.schemas.ingestion import IngestionResponse

router = APIRouter()


@router.post("/documents", response_model=IngestionResponse)
def ingest_documents() -> IngestionResponse:
    """Ingestion endpoint placeholder; pipeline implementation comes next."""
    return IngestionResponse(status="not_implemented", documents=0, chunks=0)