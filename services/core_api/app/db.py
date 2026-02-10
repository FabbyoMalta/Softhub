from __future__ import annotations

from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class BillingAction(Base):
    __tablename__ = 'billing_actions'

    action_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)


settings = get_settings()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
