from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Softhub Ops Console API'
    env: str = 'dev'

    ixc_host: str = Field(default='mock.ixc.local', alias='IXC_HOST')
    ixc_user: str = Field(default='usuario', alias='IXC_USER')
    ixc_token: str = Field(default='token', alias='IXC_TOKEN')
    ixc_verify_tls: bool = Field(default=True, alias='IXC_VERIFY_TLS')
    ixc_timeout_s: float = Field(default=20.0, alias='IXC_TIMEOUT_S')
    ixc_mode: str = Field(default='mock', alias='IXC_MODE')

    ixc_client_endpoint: str = Field(default='cliente', alias='IXC_CLIENT_ENDPOINT')

    billing_ticket_batch_limit: int = Field(default=50, alias='BILLING_TICKET_BATCH_LIMIT')
    billing_ticket_endpoint: str = Field(default='su_ticket', alias='BILLING_TICKET_ENDPOINT')
    billing_ticket_action: str = Field(default='inserir', alias='BILLING_TICKET_ACTION')
    billing_ticket_setor_id: str | None = Field(default=None, alias='BILLING_TICKET_SETOR_ID')
    billing_ticket_assunto_id: str | None = Field(default=None, alias='BILLING_TICKET_ASSUNTO_ID')
    billing_ticket_prioridade: str = Field(default='M', alias='BILLING_TICKET_PRIORIDADE')
    billing_ticket_enable: bool = Field(default=False, alias='BILLING_TICKET_ENABLE')
    billing_ticket_daily_limit: int = Field(default=20, alias='BILLING_TICKET_DAILY_LIMIT')
    billing_ticket_mensagem_template: str = Field(
        default='Cobranca preventiva: cliente={id_cliente} contrato={id_contrato} titulo={external_id} vencimento={due_date} dias={open_days} valor={amount_open} filial={filial_id} plano={plano_nome}',
        alias='BILLING_TICKET_MENSAGEM_TEMPLATE',
    )
    billing_ticket_close_endpoint: str = Field(default='su_ticket', alias='BILLING_TICKET_CLOSE_ENDPOINT')
    billing_ticket_close_action: str = Field(default='editar', alias='BILLING_TICKET_CLOSE_ACTION')

    billing_autoclose_enabled: bool = Field(default=False, alias='BILLING_AUTOCLOSE_ENABLED')
    billing_autoclose_limit: int = Field(default=50, alias='BILLING_AUTOCLOSE_LIMIT')

    redis_url: str = Field(default='redis://redis:6379/0', alias='REDIS_URL')
    database_url: str = Field(default='postgresql+psycopg://postgres:postgres@postgres:5432/softhub', alias='DATABASE_URL')
    softhub_profile: bool = Field(default=False, alias='SOFTHUB_PROFILE')
    dashboard_cache_ttl_s: int = Field(default=60, alias='DASHBOARD_CACHE_TTL_S')
    frontend_dev_url: str = Field(default='http://localhost:5173', alias='FRONTEND_DEV_URL')
    billing_case_seed_dev: bool = Field(default=False, alias='BILLING_CASE_SEED_DEV')

    cors_allow_origins: str = Field(default='', alias='CORS_ALLOW_ORIGINS')
    cors_allow_credentials: bool = Field(default=False, alias='CORS_ALLOW_CREDENTIALS')
    cors_allow_methods: str = Field(default='*', alias='CORS_ALLOW_METHODS')
    cors_allow_headers: str = Field(default='*', alias='CORS_ALLOW_HEADERS')

    ixc_slow_threshold_ms: int = Field(default=1500, alias='IXC_SLOW_THRESHOLD_MS')


@lru_cache
def get_settings() -> Settings:
    return Settings()
