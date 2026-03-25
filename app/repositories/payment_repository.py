from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, PaymentStatus, ProviderStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        merchant_id: UUID,
        external_invoice_id: str,
        amount: Decimal,
    ) -> Payment:
        payment = Payment(
            merchant_id=merchant_id,
            external_invoice_id=external_invoice_id,
            amount=amount,
            status=PaymentStatus.PENDING,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Optional[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment: Payment,
        status: PaymentStatus,
        provider_status: Optional[ProviderStatus] = None,
        failure_reason: Optional[str] = None,
    ) -> None:
        payment.status = status
        if provider_status:
            payment.provider_status = provider_status
        if failure_reason:
            payment.failure_reason = failure_reason

    async def set_provider_payment_id(self, payment: Payment, provider_payment_id: str) -> None:
        payment.provider_payment_id = provider_payment_id
