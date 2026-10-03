from contextvars import ContextVar

user_claims: ContextVar[dict | None] = ContextVar("user_claims", default=None)
