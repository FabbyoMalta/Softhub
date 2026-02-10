from fastapi import FastAPI

from app.api.billing import router as billing_router
from app.config import get_settings
from app.db import init_db

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(billing_router)


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.get('/healthz')
def healthz():
    return {'status': 'ok'}
