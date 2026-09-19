import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.middlerware.request_context import user_context_middleware
from app.routes.admin import admin_references_router
from app.routes.admin import router as admin_location_router
from app.routes.locations import router as locations_router
from app.routes.references import router as references_router
from app.utils.logging import LOGGING_CONFIG
from config import settings

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("location-service is starting up")
    yield
    logger.info("location-service is shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/locations/docs",
        redoc_url="/api/locations/redoc",
        openapi_url="/api/locations/openapi.json",
    )

    app.middleware("http")(user_context_middleware)

    @app.get("/locations/health")
    async def health_check():
        return {"status": "ok"}

    app.include_router(locations_router)

    app.include_router(references_router)

    app.include_router(admin_location_router)

    app.include_router(admin_references_router)

    return app


app = create_app()
