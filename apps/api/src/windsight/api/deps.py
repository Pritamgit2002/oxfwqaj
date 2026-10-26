from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from windsight.core.config import Settings, get_settings
from windsight.db.session import get_session
from windsight.repositories.generation import GenerationRepository
from windsight.services.analytics import AnalyticsService

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_analytics(session: SessionDep, settings: SettingsDep) -> AnalyticsService:
    return AnalyticsService(GenerationRepository(session), settings)


AnalyticsDep = Annotated[AnalyticsService, Depends(get_analytics)]
