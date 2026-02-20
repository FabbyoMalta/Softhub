import uuid
import time
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from starlette.requests import Request

from app.api.billing import router as billing_router
from app.api.debug import router as debug_router
from app.api.dashboard import router as dashboard_router
from app.api.filters import router as filters_router
from app.api.settings import router as settings_router
from app.api.oss import router as oss_router
from app.config import get_settings
from app.db import init_db
from app.services.adapters import close_ixc_resources
from app.utils.profiling import set_request_id

logger = logging.getLogger(__name__)

settings = get_settings()
WEBAPP_DIST_DIR = Path(__file__).resolve().parents[2] / 'webapp' / 'dist'
WEBAPP_INDEX_FILE = WEBAPP_DIST_DIR / 'index.html'
EXCLUDED_FRONTEND_PREFIXES = {'billing', 'dashboard', 'filters', 'settings', 'debug', 'healthz', 'docs', 'redoc', 'openapi.json', 'oss'}

app = FastAPI(title=settings.app_name)

cors_origins = [x.strip() for x in settings.cors_allow_origins.split(',') if x.strip()]
allow_origins = cors_origins or ['*']
allow_methods = [x.strip() for x in settings.cors_allow_methods.split(',') if x.strip()] or ['*']
allow_headers = [x.strip() for x in settings.cors_allow_headers.split(',') if x.strip()] or ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)

app.include_router(billing_router)
app.include_router(debug_router)
app.include_router(dashboard_router)
app.include_router(filters_router)
app.include_router(settings_router)
app.include_router(oss_router)


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.middleware('http')
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
    started = time.perf_counter()
    set_request_id(request_id)
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info('request method=%s path=%s status=%s duration_ms=%.2f', request.method, request.url.path, response.status_code, elapsed_ms)
    response.headers['X-Request-Id'] = request_id
    response.headers['X-Response-Time-Ms'] = f"{elapsed_ms:.2f}"
    return response


@app.on_event('shutdown')
def shutdown() -> None:
    close_ixc_resources()


@app.get('/healthz')
def healthz():
    return {'status': 'ok'}


@app.get('/{full_path:path}', include_in_schema=False)
def spa_fallback(full_path: str):
    normalized = full_path.strip('/')
    requested_path = normalized or 'index.html'

    if normalized and normalized.split('/', 1)[0] in EXCLUDED_FRONTEND_PREFIXES:
        raise HTTPException(status_code=404, detail='Not Found')

    if WEBAPP_DIST_DIR.exists():
        candidate = (WEBAPP_DIST_DIR / requested_path).resolve()
        if WEBAPP_DIST_DIR.resolve() in candidate.parents and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)

    if normalized and '.' in normalized:
        raise HTTPException(status_code=404, detail='Not Found')

    if WEBAPP_INDEX_FILE.exists():
        return FileResponse(WEBAPP_INDEX_FILE)

    if not normalized:
        return RedirectResponse(settings.frontend_dev_url.rstrip('/'))

    return RedirectResponse(f"{settings.frontend_dev_url.rstrip('/')}/{normalized}")
