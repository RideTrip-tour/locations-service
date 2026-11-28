from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.celery.base_task import AsyncDatabaseTask


class DummyTask(AsyncDatabaseTask):
    async def run_async(self, db, value: int):
        return value, db


class FailingTask(AsyncDatabaseTask):
    async def run_async(self, db, value: int):
        raise RuntimeError("Task failed")


@pytest.fixture
def session_context(db):
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=db)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


@pytest.mark.asyncio
async def test_execute_success(db, session_context):
    task = DummyTask()

    with patch(
        "app.celery.base_task.AsyncSessionLocalCelery",
        return_value=session_context,
    ) as session_factory:
        result = await task._execute(10)

    assert result == (10, db)

    session_factory.assert_called_once_with()
    session_context.__aenter__.assert_awaited_once()
    session_context.__aexit__.assert_awaited_once_with(
        None,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_execute_exception_closes_session(session_context):
    task = FailingTask()

    with (
        patch(
            "app.celery.base_task.AsyncSessionLocalCelery",
            return_value=session_context,
        ),
        pytest.raises(RuntimeError, match="Task failed"),
    ):
        await task._execute(10)

    session_context.__aenter__.assert_awaited_once()
    session_context.__aexit__.assert_awaited_once()

    exc_type, exc_value, traceback = session_context.__aexit__.await_args.args

    assert exc_type is RuntimeError
    assert str(exc_value) == "Task failed"
    assert traceback is not None


def test_run_executes_async_task(db, session_context):
    task = DummyTask()

    with patch(
        "app.celery.base_task.AsyncSessionLocalCelery",
        return_value=session_context,
    ):
        result = task.run(10)

    assert result == (10, db)

    session_context.__aenter__.assert_awaited_once()
    session_context.__aexit__.assert_awaited_once_with(
        None,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_run_async_not_implemented(db):
    task = AsyncDatabaseTask()

    with pytest.raises(NotImplementedError):
        await task.run_async(db)
