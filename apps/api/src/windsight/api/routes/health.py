from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from windsight.api.deps import SessionDep

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str


@router.get("/health", response_model=HealthOut)
def liveness() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/health/ready", response_model=HealthOut)
def readiness(session: SessionDep) -> HealthOut:
    session.execute(text("SELECT 1"))
    return HealthOut(status="ready")
