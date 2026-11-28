from app.celery.app import app as celery_app
from app.publishers.connectors import CeleryConnector
from app.publishers.task_publisher import TaskPublisher

celery_connector = CeleryConnector(producer=celery_app)

task_publisher = TaskPublisher(
    connector=celery_connector,
)
