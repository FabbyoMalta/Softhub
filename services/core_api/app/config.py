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

    redis_url: str = Field(default='redis://redis:6379/0', alias='REDIS_URL')
    database_url: str = Field(default='postgresql+psycopg://postgres:postgres@postgres:5432/softhub', alias='DATABASE_URL')
    softhub_profile: bool = Field(default=False, alias='SOFTHUB_PROFILE')
    dashboard_cache_ttl_s: int = Field(default=60, alias='DASHBOARD_CACHE_TTL_S')
    frontend_dev_url: str = Field(default='http://localhost:5173', alias='FRONTEND_DEV_URL')
    billing_case_seed_dev: bool = Field(default=False, alias='BILLING_CASE_SEED_DEV')


@lru_cache
def get_settings() -> Settings:
    return Settings()
