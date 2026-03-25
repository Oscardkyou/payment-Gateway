from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.models.payment import PaymentStatus, ProviderStatus


class PayoutRequest(BaseModel):
    external_invoice_id: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, decimal_places=2)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class PayoutResponse(BaseModel):
    id: UUID
    external_invoice_id: str
    amount: Decimal
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentDetailResponse(BaseModel):
    id: UUID
    external_invoice_id: str
    provider_payment_id: Optional[str]
    amount: Decimal
    status: PaymentStatus
    provider_status: Optional[ProviderStatus]
    failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderPaymentRequest(BaseModel):
    payment_id: str
    amount: Decimal
    callback_url: str


class ProviderPaymentResponse(BaseModel):
    provider_payment_id: str
    status: ProviderStatus
    message: str


class ProviderWebhookRequest(BaseModel):
    provider_payment_id: str
    status: ProviderStatus
    failure_reason: Optional[str] = None
