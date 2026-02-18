from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class BillingAction(Base):
    __tablename__ = 'billing_actions'

    action_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)


class SavedFilter(Base):
    __tablename__ = 'saved_filters'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Setting(Base):
    __tablename__ = 'settings'

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class BillingCase(Base):
    __tablename__ = 'billing_case'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    id_cliente: Mapped[str] = mapped_column(String(64), nullable=False)
    id_contrato: Mapped[str | None] = mapped_column(String(64), nullable=True)
    filial_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_open: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal('0'))
    open_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status_case: Mapped[str] = mapped_column(String(32), nullable=False, default='OPEN')
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    action_state: Mapped[str] = mapped_column(String(64), nullable=False, default='NONE')
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    contract_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    client_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contract_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ticket_status: Mapped[str | None] = mapped_column(String(32), nullable=True)


class BillingActionLog(Base):
    __tablename__ = 'billing_action_log'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey('billing_case.id'), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


settings = get_settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _seed_billing_cases_for_dev()


def _seed_billing_cases_for_dev() -> None:
    if settings.env != 'dev' or not settings.billing_case_seed_dev:
        return

    with SessionLocal() as db:
        if db.query(BillingCase.id).first() is not None:
            return

        now = datetime.utcnow()
        db.add_all(
            [
                BillingCase(
                    external_id='SEED-1001',
                    id_cliente='C-1001',
                    id_contrato='CT-1001',
                    filial_id='1',
                    due_date=date.today() - timedelta(days=7),
                    amount_open=Decimal('149.90'),
                    open_days=7,
                    payment_type='BOLETO',
                    status_case='OPEN',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='NONE',
                    snapshot_json={'source': 'seed'},
                ),
                BillingCase(
                    external_id='SEED-1002',
                    id_cliente='C-1002',
                    filial_id='2',
                    due_date=date.today() - timedelta(days=21),
                    amount_open=Decimal('89.00'),
                    open_days=21,
                    payment_type='PIX',
                    status_case='OPEN',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='NOTIFIED',
                    snapshot_json={'source': 'seed'},
                ),
            ]
        )
        db.commit()
