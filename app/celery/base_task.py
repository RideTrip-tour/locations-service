import asyncio
import logging

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocalCelery

logger = logging.getLogger(__name__)


class AsyncDatabaseTask(Task):
    def run(self, *args, **kwargs):
        return asyncio.run(self._execute(*args, **kwargs))

    async def _execute(self, *args, **kwargs):
        async with AsyncSessionLocalCelery() as session:
            return await self.run_async(
                session,
                *args,
                **kwargs,
            )

    async def run_async(self, db: AsyncSession, *args, **kwargs):
        raise NotImplementedError

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Task %s [%s] retrying. Attempt %s/%s. Error: %s",
            self.name,
            task_id,
            self.request.retries,
            self.max_retries,
            exc,
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task %s [%s] failed after %s retries. Error: %s",
            self.name,
            task_id,
            self.request.retries,
            exc,
            exc_info=(
                type(exc),
                exc,
                exc.__traceback__,
            ),
        )

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "Task %s [%s] completed successfully",
            self.name,
            task_id,
        )
