from app.adapters.ixc_adapter import MockIXCAdapter, RealIXCAdapter
from app.clients.ixc_client import IXCClient
from app.config import get_settings

_real_client: IXCClient | None = None


def get_ixc_adapter():
    global _real_client
    settings = get_settings()
    if settings.ixc_mode.lower() == 'real':
        if _real_client is None:
            _real_client = IXCClient(
                host=settings.ixc_host,
                user=settings.ixc_user,
                token=settings.ixc_token,
                verify_tls=settings.ixc_verify_tls,
                timeout_s=settings.ixc_timeout_s,
            )
        return RealIXCAdapter(_real_client)
    return MockIXCAdapter()


def close_ixc_resources() -> None:
    global _real_client
    if _real_client is not None:
        _real_client.close()
        _real_client = None
