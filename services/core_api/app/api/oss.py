from __future__ import annotations

from fastapi import APIRouter, Depends

from app.services.adapters import get_ixc_adapter

router = APIRouter(prefix='/oss', tags=['oss'])


@router.get('/{id_chamado}/mensagens')
def get_oss_mensagens(id_chamado: str, adapter=Depends(get_ixc_adapter)):
    registros = adapter.list_oss_mensagens(id_chamado)
    registros = sorted(registros, key=lambda r: str(r.get('data') or ''))
    return {'total': len(registros), 'registros': registros}
