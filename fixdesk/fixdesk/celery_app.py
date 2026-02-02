import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

celery = Celery(
    "fixdesk_api",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Lagos",
    enable_utc=True,

    # Production reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Must be > max task runtime (in seconds)
    broker_transport_options={"visibility_timeout": 3600},

    # Prevent memory creep
    worker_max_tasks_per_child=500,

    # Don't store results forever
    result_expires=3600,
)
