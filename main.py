# src/main.py
from contextlib import asynccontextmanager
import logging.config
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from config import settings
from app.utils.logging import LOGGING_CONFIG
from app.routes.location_routes import router as location_router

logging.config.dictConfig(LOGGING_CONFIG)


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        x_user_id = request.headers.get("x-user-id")

        request.state.user_id = x_user_id

        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Service is starting up...")

    yield

    logging.info("Service is shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    return app


app = create_app()
app.add_middleware(GatewayAuthMiddleware)
app.include_router(location_router)
