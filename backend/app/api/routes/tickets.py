from fastapi import APIRouter

from app.core.admin_metrics import record_ticket
from app.schemas.tickets import TicketRequest, TicketResponse

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse)
def create_ticket(request: TicketRequest) -> TicketResponse:
    reference_id = record_ticket(
        title=request.title,
        description=request.description,
        source=request.source,
    )
    return TicketResponse(reference_id=reference_id, status="submitted")
