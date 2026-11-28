import pytest

from app.celery.app import app as celery_app


def test_celery_app_name():
    assert celery_app.main == "location"


@pytest.mark.parametrize(
    ("task_default",),
    [
        ("task_default_queue",),
        ("task_default_exchange",),
        ("task_default_routing_key",),
    ],
)
def test_default_task(task_default):
    assert getattr(celery_app.conf, task_default) == "location"


@pytest.mark.parametrize(
    ("task_name", "expected_queue"),
    [
        ("location.some_task", "location"),
        ("profile.some_task", "profile"),
        ("profile.delete_favorite_locations", "profile"),
    ],
)
def test_task_routes(task_name: str, expected_queue: str):
    route = celery_app.amqp.router.route({}, task_name)

    assert route["queue"].name == expected_queue


def test_task_serialization():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.result_serializer == "json"


def test_timezone():
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


def test_task_execution_options():
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_broker_connection_retry():
    assert celery_app.conf.broker_connection_retry_on_startup is True


def test_broker_transport_options():
    assert celery_app.conf.broker_transport_options == {
        "visibility_timeout": 3600,
    }


def test_result_expires():
    assert celery_app.conf.result_expires == 86400
