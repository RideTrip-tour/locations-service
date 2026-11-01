import logging

from internal_client import InternalClient
from internal_middleware import user_claims

from config import settings

logger = logging.getLogger("location_service")


class GatewayClient(InternalClient):
    def __init__(self):
        super().__init__(
            base_url=settings.gateway_url,
            service_id=settings.service_id,
            service_token=settings.service_token,
            gateway_name=settings.gateway_name,
            access_token_expire_sec=settings.access_token_expire_sec,
            jwt_secret=settings.jwt_secret,
            timeout=10.0,
        )

    def _get_user_context(self) -> str:
        return self._build_user_context(user_claims.get())
