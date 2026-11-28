from celery import Celery
from kombu import Exchange, Queue

from config import settings

app = Celery(
    "location",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

app.conf.update(
    task_queues=(
        Queue("profile", Exchange("profile"), routing_key="profile"),
        Queue("location", Exchange("location"), routing_key="location"),
    ),
    task_default_queue="location",
    task_default_exchange="location",
    task_default_routing_key="location",
    task_routes={
        "profile.*": {"queue": "profile"},
        "location.*": {"queue": "location"},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=86400,
)
