# SOFTHUB (Ops Console) — MVP

Monorepo com FastAPI + Postgres + Redis + Celery + Vite/React TS, com integração IXCsoft via `grid_param`.

## Estrutura

- `services/core_api`: API principal.
- `services/worker`: Celery worker.
- `services/webapp`: frontend React.
- `docker-compose.yml`: stack completa em modo mock por padrão.

## Funcionalidades MVP

- `GET /billing/open`: lista contas a receber em aberto (`valor_aberto > 0`) com enrich de contrato (`fn_areceber -> cliente_contrato`) e agregados:
  - `total_open`
  - `over_20_days`
  - `oldest_due_date`
- Idempotência para ação de automação de 20 dias usando tabela `billing_actions`.
- `IXCClient` robusto com `httpx`, retry/backoff e paginação por `registros`/`total`.
- Helpers de `grid_param` para contratos, contas, atrasos, OS e tickets.

## Rodando (modo MOCK)

```bash
docker compose up --build
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

Padrão de integração implementado:

- URL: `https://{IXC_HOST}/webservice/v1/<endpoint>`
- Headers:
  - `Authorization: Basic base64(usuario:token)`
  - `Content-Type: application/json`
  - `ixcsoft: listar`
- Payload:
  - `grid_param` (JSON string)
  - `page`, `rp` (string)
  - `sortname`, `sortorder`

## TODOs explícitos (mapeamento por ambiente)

1. Confirmar TB/campos reais de `su_oss_chamado` para filtros de data agendada/status/tipo.
2. Confirmar TB/campo real de status de `su_ticket`.
3. Validar semântica local de `status` em `fn_areceber` (MVP usa `valor_aberto > 0` como regra principal).
4. Evoluir fallback de join sem `id_contrato` usando `id_cliente`.
5. Confirmar se operador `IN` é suportado na instância IXC local; caso não, manter batching/cache.

## Endpoints IXC usados (RealIXCAdapter)

- Contratos: `/cliente_contrato`
- Ordens de serviço: `/su_oss_chamado`
- Atendimentos/tickets: `/su_ticket`
- Contas a receber: `/fn_areceber`
