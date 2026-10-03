from fastapi import Request

from app.client.gateway_client import GatewayClient


def get_gateway_client(request: Request) -> GatewayClient:
    """Return the application-wide gateway client."""
    return request.app.state.gateway_client
