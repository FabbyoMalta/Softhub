# SOFTHUB (Ops Console) — MVP

Monorepo com FastAPI + Postgres + Redis + Celery + Vite/React TS, com integração IXCsoft via `grid_param`.

## Estrutura

- `services/core_api`: API principal.
- `services/worker`: Celery worker.
- `services/webapp`: frontend React.
- `docker-compose.yml`: stack completa em modo mock por padrão.

## Funcionalidades MVP

### Billing

- `GET /billing/open`: lista contas a receber em aberto (`valor_aberto > 0`) com enrich de contrato.
- Idempotência para ação de automação de 20 dias usando tabela `billing_actions`.

### Dashboard (agenda semanal + manutenções)

- `GET /dashboard/agenda-week?start=YYYY-MM-DD&days=7&filter_id=&filter_json=`
- `GET /dashboard/maintenances?from=YYYY-MM-DD&to=YYYY-MM-DD&filter_id=&filter_json=`
- Filtros salvos:
  - `GET /filters?scope=agenda_week|maintenances`
  - `POST /filters` com `{name, scope, definition_json}`
  - `DELETE /filters/{id}`

Regras aplicadas:
- backend sempre envia `grid_param` para `/su_oss_chamado` (filtro pesado no IXC)
- backend enriquece OS com dados de cliente via endpoint `/cliente`
- frontend envia apenas filtro humano (`definition_json`)

## Mapeamentos (MVP)

Arquivo central: `services/core_api/app/services/dashboard.py`

- `STATUS_LABELS`: mapeia código -> nome
- `STATUS_GROUPS`:
  - `open_like = ["A","AN","EN","AS","DS","EX","RAG"]`
  - `scheduled = ["AG","RAG"]`
  - `done = ["F"]`
- `ASSUNTO_CATEGORIES`:
  - `"1" -> "instalacao"`
  - `"15" -> "mudanca_endereco"`
  - `"17" -> "sem_conexao"`
  - `"34" -> "quedas_constantes"`
  - `"31" -> "analise_suporte"`
- `INSTALL_ASSUNTOS = {"1"}`
- `MAINTENANCE_ASSUNTOS = {"17","34","31"}`

Para ajustar no seu ambiente IXC, altere os dicionários/sets acima.

## Grid builder central

Arquivo: `services/core_api/app/services/ixc_grid_builder.py`

Constantes TB:
- `TB_OS_DATA_AGENDA = su_oss_chamado.data_agenda`
- `TB_OS_STATUS = su_oss_chamado.status`
- `TB_OS_ID_ASSUNTO = su_oss_chamado.id_assunto`
- `TB_OS_ID_CLIENTE = su_oss_chamado.id_cliente`

## Rodando (modo MOCK)

```bash
docker compose up -d --build
```

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173/dashboard`

## Modo REAL (IXC)

No `docker-compose.yml` (ou `.env` da API), altere:

- `IXC_MODE=real`
- `IXC_HOST=<seu-host-ixc>`
- `IXC_USER=<usuario-webservice>`
- `IXC_TOKEN=<token-webservice>`
- `IXC_VERIFY_TLS=true|false`

## Profiling e cache da dashboard

Variáveis novas na API:

- `SOFTHUB_PROFILE=1` ativa logs estruturados de profiling e endpoint de debug.
- `DASHBOARD_CACHE_TTL_S=60` define TTL do cache do summary (sugestão: 30–120).

Com profiling ativo:

- logs mostram etapas com `elapsed_ms` (IXC/paginação/merge/summary)
- endpoint `GET /debug/perf/last?limit=100` retorna últimos eventos de timing

No endpoint `GET /dashboard/summary`, confira header:

- `X-Cache: HIT` quando veio do Redis
- `X-Cache: MISS` quando calculou e gravou no cache

## Testes principais

```bash
cd services/core_api
python -m pytest -q
```
