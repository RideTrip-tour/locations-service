import logging
import time

import httpx
import jwt

from app.exceptions import UserContextIncompleteError, UserContextMissingError
from app.middlerware.context import user_claims
from config import settings

logger = logging.getLogger("location_service")


class GatewayClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "client"):
            self.client = httpx.AsyncClient(
                base_url=settings.gateway_url,
                timeout=10.0,
            )

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-Service-ID": settings.service_id,
            "X-Service-Token": settings.service_token,
            "X-User-Context": self._get_user_context(),
        }

    def _get_user_context(self) -> str:
        claims = user_claims.get()
        if not claims:
            raise UserContextMissingError()
        if not all(
            required_claim in claims
            for required_claim in ("id", "is_active", "is_superuser")
        ):
            raise UserContextIncompleteError()
        data = {
            "sub": str(claims["id"]),
            "is_active": bool(claims["is_active"]),
            "is_superuser": bool(claims["is_superuser"]),
            "aud": settings.gateway_name,
            "exp": int(time.time()) + settings.access_token_expire_sec,
        }
        return jwt.encode(
            data,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, int] | None = None,
    ) -> httpx.Response:
        started_at = time.monotonic()
        headers = self._get_headers()

        logger.info(
            "Gateway request started: %s: %s",
            method,
            path,
        )

        try:
            response = await self.client.request(
                method, path, headers=headers, params=params
            )
            elapsed = time.monotonic() - started_at
            logger.info(
                "Gateway request completed: %s: %s -> %s in %s s",
                method,
                path,
                response.status_code,
                elapsed,
            )
            response.raise_for_status()
            return response
        except Exception:
            elapsed = time.monotonic() - started_at

            logger.exception(
                "Gateway request failed: %s: %s in %s s",
                method,
                path,
                elapsed,
            )
            raise

    async def close(self) -> None:
        await self.client.aclose()
