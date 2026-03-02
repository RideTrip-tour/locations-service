# src/app/middlewares/auth.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропускаем эндпоинты документации
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Читаем заголовок от API Gateway
        x_user_id = request.headers.get("x-user-id")

        # Записываем в state, чтобы использовать в роутерах
        request.state.user_id = x_user_id

        response = await call_next(request)
        return response
