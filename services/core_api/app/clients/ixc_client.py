from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import httpx

from app.config import get_settings
from app.utils.profiling import log_profile_event, now_ms

logger = logging.getLogger(__name__)


class IXCClientError(RuntimeError):
    pass


class IXCClient:
    def __init__(
        self,
        host: str,
        user: str,
        token: str,
        verify_tls: bool = True,
        timeout_s: float = 20.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ) -> None:
        self.base_url = f'https://{host}/webservice/v1'
        self.verify_tls = verify_tls
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.auth_header = build_basic_auth_header(user, token)
        self._client = httpx.Client(verify=self.verify_tls, timeout=self.timeout_s)

    def _headers(self, action: str = 'listar') -> dict[str, str]:
        return {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json',
            'ixcsoft': action,
        }

    def close(self) -> None:
        self._client.close()

    def post_list(
        self,
        endpoint: str,
        grid_filters: list[dict[str, Any]],
        page: int,
        rp: int,
        sortname: str,
        sortorder: str,
        action: str = 'listar',
    ) -> dict[str, Any]:
        payload = {
            'grid_param': json.dumps(grid_filters),
            'page': str(page),
            'rp': str(rp),
            'sortname': sortname,
            'sortorder': sortorder,
        }
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        for attempt in range(1, self.max_retries + 1):
            started = now_ms()
            try:
                response = self._client.post(url, headers=self._headers(action=action), json=payload)
                elapsed_ms = now_ms() - started
                if get_settings().softhub_profile:
                    log_profile_event(
                        logger,
                        {
                            'component': 'ixc.post_list',
                            'endpoint_ixc': endpoint,
                            'status_code': response.status_code,
                            'elapsed_ms': elapsed_ms,
                            'content_size': len(response.content or b''),
                            'page': page,
                            'rp': rp,
                        },
                    )
                if elapsed_ms >= get_settings().ixc_slow_threshold_ms:
                    logger.warning('IXC slow call endpoint=%s status=%s elapsed_ms=%s page=%s rp=%s', endpoint, response.status_code, elapsed_ms, page, rp)
                if response.status_code in {408, 429} or response.status_code >= 500:
                    raise IXCClientError(
                        f'IXC retryable status for {endpoint} on attempt {attempt}: {response.status_code}'
                    )

                response.raise_for_status()

                # Diagnóstico quando o IXC retorna HTML/vazio/texto
                headers = getattr(response, "headers", {}) or {}
                ct = headers.get("content-type", "")
                text = getattr(response, "text", "")
                try:
                    data = response.json()
                except Exception as exc:
                    logger.error(
                        'IXC non-json response endpoint=%s status_code=%s content_type=%s body_start=%r',
                        endpoint,
                        response.status_code,
                        ct,
                        text[:200],
                    )
                    if get_settings().softhub_profile:
                        log_profile_event(
                            logger,
                            {
                                'component': 'ixc.post_list.non_json',
                                'endpoint_ixc': endpoint,
                                'status_code': response.status_code,
                                'elapsed_ms': elapsed_ms,
                                'body_start': text[:200],
                            },
                        )
                    raise IXCClientError(
                        f"IXC returned non-JSON for endpoint={endpoint} "
                        f"url={url} status={response.status_code} content-type={ct} "
                        f"body_start={text[:200]!r}"
                    ) from exc

                if isinstance(data, dict) and data.get("type") == "error":
                    raise IXCClientError(
                        f"IXC logical error for {endpoint} on attempt {attempt}: {data.get('message', 'unknown error')}"
                    )

                return data
            except (httpx.TimeoutException, httpx.NetworkError, IXCClientError) as exc:
                if attempt >= self.max_retries:
                    raise IXCClientError(f'Failed IXC call for {endpoint} on attempt {attempt}: {exc}') from exc
                time.sleep(self.backoff_base * (2 ** (attempt - 1)))
            except httpx.HTTPStatusError as exc:
                raise IXCClientError(f'IXC HTTP error for {endpoint} on attempt {attempt}: {exc}') from exc
        raise IXCClientError(f'Unexpected IXC failure for {endpoint}')

    def iterate_all(
        self,
        endpoint: str,
        grid_filters: list[dict[str, Any]],
        rp: int = 1000,
        sortname: str = 'id',
        sortorder: str = 'asc',
    ) -> list[dict[str, Any]]:
        started = now_ms()
        page = 1
        all_records: list[dict[str, Any]] = []
        expected_total: int | None = None
        pages_fetched = 0
        while True:
            data = self.post_list(endpoint, grid_filters, page, rp, sortname, sortorder)
            pages_fetched += 1
            registros = data.get('registros') or []
            if expected_total is None:
                try:
                    expected_total = int(data.get('total', len(registros)))
                except (TypeError, ValueError):
                    expected_total = len(registros)
            all_records.extend(registros)
            if not registros or len(all_records) >= expected_total:
                break
            page += 1
        if get_settings().softhub_profile:
            log_profile_event(
                logger,
                {
                    'component': 'ixc.iterate_all',
                    'endpoint_ixc': endpoint,
                    'pages_fetched': pages_fetched,
                    'expected_total': expected_total,
                    'total_records_returned': len(all_records),
                    'elapsed_ms_total': now_ms() - started,
                    'rp': rp,
                },
            )
        return all_records


def build_basic_auth_header(usuario: str, token: str) -> str:
    raw = f'{usuario}:{token}'.encode('utf-8')
    encoded = base64.b64encode(raw).decode('utf-8')
    return f'Basic {encoded}'
