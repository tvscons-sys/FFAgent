from fastapi import APIRouter

from app.core.admin_metrics import dashboard

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
def metrics(days: int = 30) -> dict:
    """Read-only dashboard data; customer chat does not depend on this route."""
    return dashboard(max(1, min(days, 365)))
