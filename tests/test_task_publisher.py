from unittest.mock import AsyncMock

import pytest

from app.publishers.connectors import PublishResult


@pytest.mark.asyncio
async def test_delete_favorite_locations_publishes_task(
    task_publisher,
    celery_connector,
):
    expected_result = PublishResult(message_id="task-123")
    celery_connector.publish = AsyncMock(return_value=expected_result)

    result = await task_publisher.delete_favorite_locations(location_id=42)

    assert result == expected_result

    celery_connector.publish.assert_awaited_once_with(
        queue="profile",
        task_name="profile.delete_favorite_locations",
        kwargs={"location_id": 42},
        countdown=None,
    )
