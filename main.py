# src/main.py
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.middlerware.request_context import user_context_middleware
from app.routes.locations import router as locations_router
from app.utils.logging import LOGGING_CONFIG
from app.routes.location_routes import router as location_router
from app.middlerware.auth import GatewayAuthMiddleware

# Инициализируем логирование при старте модуля
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("location_service")



@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Service is starting up...")
    yield
    logging.info("Service is shutting down...")


def create_app() -> FastAPI:
    """Фабрика для создания и настройки приложения."""
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/api/locations/docs",
        redoc_url="/api/locations/redoc",
        openapi_url="/api/locations/openapi.json",
    )

    # 1. Добавляем мидлвари
    app.add_middleware(GatewayAuthMiddleware)

    # 2. Подключаем роутеры
    app.include_router(location_router)

    return app


# Создаем инстанс приложения для сервера (Uvicorn/Gunicorn)
app = create_app()
