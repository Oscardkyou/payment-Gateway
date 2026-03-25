from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class MerchantInfoResponse(BaseModel):
    id: UUID
    total_amount: Decimal
    reserved_amount: Decimal
    available_amount: Decimal

    class Config:
        from_attributes = True
