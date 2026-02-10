from fastapi import FastAPI

from app.api.billing import router as billing_router
from app.config import get_settings
from app.db import init_db
from app.services.adapters import close_ixc_resources

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(billing_router)


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.on_event('shutdown')
def shutdown() -> None:
    close_ixc_resources()


@app.get('/healthz')
def healthz():
    return {'status': 'ok'}
