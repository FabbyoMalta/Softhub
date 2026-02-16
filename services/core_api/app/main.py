import uuid
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
from app.config import get_settings
from app.db import init_db
from app.services.adapters import close_ixc_resources
from app.utils.profiling import set_request_id

settings = get_settings()
WEBAPP_DIST_DIR = Path(__file__).resolve().parents[2] / 'webapp' / 'dist'
WEBAPP_INDEX_FILE = WEBAPP_DIST_DIR / 'index.html'
EXCLUDED_FRONTEND_PREFIXES = {'billing', 'dashboard', 'filters', 'settings', 'debug', 'healthz', 'docs', 'redoc', 'openapi.json'}

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois você restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(billing_router)
app.include_router(debug_router)
app.include_router(dashboard_router)
app.include_router(filters_router)
app.include_router(settings_router)


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.middleware('http')
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid.uuid4())
    set_request_id(request_id)
    response = await call_next(request)
    response.headers['X-Request-Id'] = request_id
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
