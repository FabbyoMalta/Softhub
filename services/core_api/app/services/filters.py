from __future__ import annotations

from sqlalchemy import delete, select

from app.db import SavedFilter, SessionLocal


def list_saved_filters(scope: str) -> list[SavedFilter]:
    with SessionLocal() as session:
        return list(session.scalars(select(SavedFilter).where(SavedFilter.scope == scope).order_by(SavedFilter.created_at.desc())))


def create_saved_filter(name: str, scope: str, definition_json: dict) -> SavedFilter:
    with SessionLocal() as session:
        row = SavedFilter(name=name, scope=scope, definition_json=definition_json)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def delete_saved_filter(filter_id: str) -> bool:
    with SessionLocal() as session:
        result = session.execute(delete(SavedFilter).where(SavedFilter.id == filter_id))
        session.commit()
        return bool(result.rowcount)


def get_saved_filter_definition(filter_id: str) -> dict | None:
    with SessionLocal() as session:
        row = session.scalar(select(SavedFilter).where(SavedFilter.id == filter_id))
        return row.definition_json if row else None
