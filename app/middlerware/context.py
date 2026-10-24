# depricated 22.10.26
from contextvars import ContextVar

user_claims: ContextVar[dict | None] = ContextVar("user_claims", default=None)
