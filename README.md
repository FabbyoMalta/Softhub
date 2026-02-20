# SOFTHUB (Ops Console)

Monorepo com FastAPI + Postgres + Redis + Celery + Vite/React (IXC via `grid_param`).

## Estrutura

- `services/core_api`: API FastAPI
- `services/worker`: worker Celery
- `services/webapp`: frontend React/Vite
- `docker-compose.yml`: ambiente de desenvolvimento
- `docker-compose.prod.yml`: ambiente de produção local/intranet

---

## Desenvolvimento (compose padrão)

```bash
docker compose up -d --build
```

Acessos:
- API: `http://localhost:8000`
- Frontend dev: `http://localhost:5173`

### API base no frontend

- Dev em portas separadas: `VITE_API_BASE=http://localhost:8000`
- Mesmo host/reverse proxy: `VITE_API_BASE=/api`

---

## Produção local/intranet

### 1) Preparar env

Copie e ajuste:

```bash
cp .env.prod.example .env.prod
```

Preencha ao menos:
- `IXC_HOST`, `IXC_USER`, `IXC_TOKEN`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `CORE_API_WORKERS` (default recomendado: `2`)

### 2) Subir stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Acesso:
- `http://<ip-da-maquina>/`

> Em produção, somente o serviço `web` é exposto (porta `80`).
> O `core_api` fica interno e é acessado via `/api` no Nginx.

---

## Nginx (produção)

Arquivo: `services/webapp/nginx.conf`

- Serve SPA com fallback `try_files ... /index.html`
- Faz reverse proxy de `/api/*` para `core_api:8000`
- `gzip on`

### Proteção opcional de `/admin` e `/billing` (basic auth)

No `nginx.conf` há bloco comentado para proteção com `.htpasswd`.

Gerar `.htpasswd`:

```bash
docker run --rm --entrypoint htpasswd httpd:2 -Bbn admin SENHA_FORTE > .htpasswd
```

Depois, monte o arquivo no container Nginx em `/etc/nginx/.htpasswd`.

> MVP atual também suporta ocultar links sensíveis via frontend com `VITE_FEATURE_ADMIN=false`.

---

## Observabilidade

### API

- Middleware registra duração por request (`duration_ms`) e adiciona header `X-Response-Time-Ms`.
- `IXCClient` mantém timeout/retry e gera warning em chamadas lentas (`IXC_SLOW_THRESHOLD_MS`).
- Em resposta não-JSON do IXC, loga claramente `status_code` e os primeiros 200 bytes do body.

### Healthcheck

- `core_api`: `GET /healthz`

---

## Testes backend

```bash
cd services/core_api
python -m pytest -q
```

## Build frontend

```bash
cd services/webapp
npm run build
```
