from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class DashboardItem(BaseModel):
    id: str
    date: str
    time: str | None = None
    type: Literal['instalacao', 'manutencao']
    status: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    city: str | None = None
    neighborhood: str | None = None
    address: str | None = None
    source: str = 'ixc'


class SavedFilterIn(BaseModel):
    name: str
    scope: Literal['agenda_week', 'maintenances']
    definition_json: dict[str, Any]


class SavedFilterOut(SavedFilterIn):
    id: str
    created_at: datetime
