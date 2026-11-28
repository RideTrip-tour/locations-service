import logging

from app.publishers.connectors import ProtocolConnector, PublishResult

logger = logging.getLogger(__name__)


class TaskPublisher:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, connector: ProtocolConnector) -> None:
        self._connector = connector

    async def delete_favorite_locations(
        self,
        location_id: int,
        countdown: int | None = None,
    ) -> PublishResult:
        return await self._connector.publish(
            queue="profile",
            task_name="profile.delete_favorite_locations",
            kwargs={"location_id": location_id},
            countdown=countdown,
        )
