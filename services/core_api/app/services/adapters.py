from app.adapters.ixc_adapter import MockIXCAdapter, RealIXCAdapter
from app.clients.ixc_client import IXCClient
from app.config import get_settings


def get_ixc_adapter():
    settings = get_settings()
    if settings.ixc_mode.lower() == 'real':
        client = IXCClient(
            host=settings.ixc_host,
            user=settings.ixc_user,
            token=settings.ixc_token,
            verify_tls=settings.ixc_verify_tls,
            timeout_s=settings.ixc_timeout_s,
        )
        return RealIXCAdapter(client)
    return MockIXCAdapter()
