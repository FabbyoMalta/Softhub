# SOFTHUB (Ops Console) — MVP

Monorepo com FastAPI + Postgres + Redis + Celery + Vite/React TS, com integração IXCsoft via `grid_param`.

## Estrutura

- `services/core_api`: API principal.
- `services/worker`: Celery worker.
- `services/webapp`: frontend React.
- `docker-compose.yml`: stack completa em modo mock por padrão.

## Funcionalidades MVP

### Billing

- `GET /billing/open`: lista contas a receber em aberto (`valor_aberto > 0`) com enrich de contrato (`fn_areceber -> cliente_contrato`) e agregados.
- Idempotência para ação de automação de 20 dias usando tabela `billing_actions`.

### Dashboard (novo)

- `GET /dashboard/agenda-week?start=YYYY-MM-DD&days=7&filter_id=&filter_json=`
  - retorna OS "flat" normalizadas para a agenda semanal.
- `GET /dashboard/maintenances?from=YYYY-MM-DD&to=YYYY-MM-DD&filter_id=&filter_json=`
  - retorna OS de manutenção normalizadas.
- Filtros salvos:
  - `GET /filters?scope=agenda_week|maintenances`
  - `POST /filters` com `{name, scope, definition_json}`
  - `DELETE /filters/{id}`

### UI Dashboard

- Página principal exibe:
  - topbar com filtro salvo, botão "Novo filtro" e "Salvar".
  - agenda da semana (7 colunas com cards de OS).
  - painel de manutenções (abas Abertas/Agendadas/Todas com novo request ao backend).
- `FilterBuilder` aplica filtro híbrido:
  - backend filtra por range/tipo/status/etc (server-side com `grid_param`).
  - frontend envia somente `definition_json` (intenção), sem montar `grid_param`.

## Rodando (modo MOCK)

```bash
docker compose up -d --build
```

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Healthcheck: `http://localhost:8000/healthz`

## Modo REAL (IXC)

No `docker-compose.yml` (ou `.env` da API), altere:

- `IXC_MODE=real`
- `IXC_HOST=<seu-host-ixc>`
- `IXC_USER=<usuario-webservice>`
- `IXC_TOKEN=<token-webservice>`
- `IXC_VERIFY_TLS=true|false` (default `true`)

No modo real, o backend traduz `definition_json` em `grid_param` no builder central:

- `services/core_api/app/services/ixc_grid_builder.py`

> Observação: há TODOs explícitos para confirmar nomes exatos de TB/campos por ambiente IXC.

## Como criar filtro salvo pela UI

1. Abrir dashboard web (`http://localhost:5173`).
2. Clicar em **Novo filtro**.
3. Definir tipo/status/cidade/assunto/etc e **Aplicar** para consulta ad-hoc.
4. Informar nome + escopo e clicar **Salvar filtro**.
5. Selecionar o filtro salvo no dropdown da topbar.

## Testes principais

```bash
cd services/core_api
python -m pytest -q
```

## Endpoints IXC usados (RealIXCAdapter)

- Contratos: `/cliente_contrato`
- Ordens de serviço: `/su_oss_chamado`
- Atendimentos/tickets: `/su_ticket`
- Contas a receber: `/fn_areceber`
