from celery import Celery

celery = Celery('softhub', broker='redis://redis:6379/0', backend='redis://redis:6379/1')


@celery.task
def ping_task() -> str:
    return 'pong'
