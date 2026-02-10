from __future__ import annotations

import base64
import json
import time
from typing import Any

import httpx


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

    def _headers(self) -> dict[str, str]:
        return {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json',
            'ixcsoft': 'listar',
        }

    def post_list(
        self,
        endpoint: str,
        grid_filters: list[dict[str, Any]],
        page: int,
        rp: int,
        sortname: str,
        sortorder: str,
    ) -> dict[str, Any]:
        payload = {
            'grid_param': json.dumps(grid_filters),
            'page': str(page),
            'rp': str(rp),
            'sortname': sortname,
            'sortorder': sortorder,
        }
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        with httpx.Client(verify=self.verify_tls, timeout=self.timeout_s) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = client.post(url, headers=self._headers(), json=payload)
                    if response.status_code >= 500:
                        raise IXCClientError(f'IXC 5xx on {endpoint}: {response.status_code}')
                    response.raise_for_status()
                    return response.json()
                except (httpx.TimeoutException, httpx.NetworkError, IXCClientError) as exc:
                    if attempt >= self.max_retries:
                        raise IXCClientError(f'Failed IXC call for {endpoint}: {exc}') from exc
                    time.sleep(self.backoff_base * (2 ** (attempt - 1)))
                except httpx.HTTPStatusError as exc:
                    raise IXCClientError(f'IXC HTTP error for {endpoint}: {exc}') from exc
        raise IXCClientError(f'Unexpected IXC failure for {endpoint}')

    def iterate_all(
        self,
        endpoint: str,
        grid_filters: list[dict[str, Any]],
        rp: int = 1000,
        sortname: str = 'id',
        sortorder: str = 'asc',
    ) -> list[dict[str, Any]]:
        page = 1
        all_records: list[dict[str, Any]] = []
        expected_total: int | None = None
        while True:
            data = self.post_list(endpoint, grid_filters, page, rp, sortname, sortorder)
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
        return all_records


def build_basic_auth_header(usuario: str, token: str) -> str:
    raw = f'{usuario}:{token}'.encode('utf-8')
    encoded = base64.b64encode(raw).decode('utf-8')
    return f'Basic {encoded}'
