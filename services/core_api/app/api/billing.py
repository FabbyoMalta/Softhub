from fastapi import APIRouter, Depends

from app.models.billing import BillingOpenResponse
from app.services.adapters import get_ixc_adapter
from app.services.billing import build_billing_open_response

router = APIRouter(prefix='/billing', tags=['billing'])


@router.get('/open', response_model=BillingOpenResponse)
def get_billing_open(adapter=Depends(get_ixc_adapter)):
    return build_billing_open_response(adapter)
