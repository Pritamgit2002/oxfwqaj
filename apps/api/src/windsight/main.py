from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from windsight import __version__
from windsight.api.middleware import add_request_context
from windsight.api.routes import analytics, health
from windsight.core.config import get_settings
from windsight.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Wind generation forecasts and their accuracy for UK day-ahead power procurement. "
            "Source data: Elexon BMRS FUELHH (actuals) and WINDFOR (forecasts)."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Server-Timing"],
    )
    add_request_context(app)
    app.include_router(health.router)
    app.include_router(analytics.router)
    return app


app = create_app()
