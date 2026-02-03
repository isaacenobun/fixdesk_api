from fixdesk.fixdesk.celery_app import celery
import time

@celery.task(bind=True)
def demo_task(self, seconds=3):
    time.sleep(seconds)
    return {"ok": True, "slept": seconds}
