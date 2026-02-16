from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class DashboardItem(BaseModel):
    id: str
    scheduled_at: str | None = None
    date: str
    time: str | None = None
    status_code: str | None = None
    status_label: str | None = None
    assunto_id: str | None = None
    type: Literal['instalacao', 'manutencao', 'outros']
    id_cliente: str | None = None
    id_filial: str | None = None
    customer_name: str | None = None
    phone: str | None = None
    address: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    protocolo: str | None = None
    source: str = 'ixc'


class SavedFilterIn(BaseModel):
    name: str
    scope: Literal['agenda_week', 'maintenances']
    definition_json: dict[str, Any]


class SavedFilterOut(SavedFilterIn):
    id: str
    created_at: datetime


class SummaryPeriod(BaseModel):
    start: str
    end: str


class SummaryInstalacoes(BaseModel):
    agendadas_hoje: int
    finalizadas_hoje: int
    total_periodo: int


class SummaryManutencoes(BaseModel):
    abertas_total: int
    abertas_hoje: int
    finalizadas_hoje: int
    total_periodo: int


class SummaryByDayItem(BaseModel):
    date: str
    count: int


class DashboardSummary(BaseModel):
    period: SummaryPeriod
    instalacoes: SummaryInstalacoes
    manutencoes: SummaryManutencoes
    installations_scheduled_by_day: list[SummaryByDayItem]
    maint_opened_by_day: list[SummaryByDayItem]
    maint_closed_by_day: list[SummaryByDayItem]


class CapacityEntry(BaseModel):
    limit: int
    count: int
    remaining: int
    fill_ratio: float
    level: Literal['green', 'yellow', 'red']


class DayCapacity(BaseModel):
    filial_1: CapacityEntry
    filial_2: CapacityEntry
    total: CapacityEntry


class AgendaDay(BaseModel):
    date: str
    items: list[DashboardItem]
    capacity: DayCapacity


class AgendaWeekResponse(BaseModel):
    days: list[AgendaDay]


class DefaultFilters(BaseModel):
    agenda: str | None = None
    manutencoes: str | None = None


class SubjectGroups(BaseModel):
    instalacao: list[str] = []
    manutencao: list[str] = []
    outros: list[str] = []


class AppSettings(BaseModel):
    default_filters: DefaultFilters
    installation_subject_ids: list[str] = []
    maintenance_subject_ids: list[str] = []
    subject_groups: SubjectGroups
    agenda_capacity: dict[str, dict[str, int]]
    filiais: dict[str, str]
