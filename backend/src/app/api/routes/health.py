from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Stable public contract for process liveness."""

    status: Literal["ok"] = "ok"
    service: Literal["document-qa-api"] = "document-qa-api"
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse, operation_id="getHealth")
async def get_health() -> HealthResponse:
    """Confirm that the API process can serve requests."""
    return HealthResponse()
