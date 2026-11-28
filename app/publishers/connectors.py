import asyncio
import logging
from typing import Protocol

from celery import Celery
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class PublishResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    message_id: str


class ProtocolConnector(Protocol):
    async def publish(
        self,
        queue: str,
        task_name: str,
        args: list | None = None,
        kwargs: dict | None = None,
        countdown: int | None = None,
    ) -> PublishResult: ...

    async def revoke(self, message_id: str) -> None: ...


class CeleryConnector:
    def __init__(self, producer: Celery) -> None:
        self._producer = producer

    async def publish(
        self,
        queue: str,
        task_name: str,
        args: list | None = None,
        kwargs: dict | None = None,
        countdown: int | None = None,
    ) -> PublishResult:
        try:
            result = await asyncio.to_thread(
                self._producer.send_task,
                task_name,
                args=args or [],
                kwargs=kwargs or {},
                queue=queue,
                countdown=countdown,
            )
            return PublishResult(message_id=str(result.id))
        except Exception:
            logger.exception(
                "Failed to publish Celery task: %s to queue: %s",
                task_name,
                queue,
            )
            raise

    async def revoke(self, message_id: str) -> None:
        try:
            await asyncio.to_thread(
                self._producer.control.revoke,
                message_id,
            )
        except Exception:
            logger.exception(
                "Failed to revoke Celery task: %s",
                message_id,
            )
            raise
