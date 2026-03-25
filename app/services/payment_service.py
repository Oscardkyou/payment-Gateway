from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.models.payment import Payment, PaymentStatus
from app.repositories.balance_repository import BalanceRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import ProviderPaymentRequest


class InsufficientBalanceError(Exception):
    pass


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.balance_repo = BalanceRepository(session)

    async def create_payout(
        self,
        merchant_id: UUID,
        external_invoice_id: str,
        amount: Decimal,
        provider_url: str,
    ) -> Payment:
        balance = await self.balance_repo.get_by_merchant_id_for_update(merchant_id)
        if not balance:
            raise ValueError("Balance not found")

        if not await self.balance_repo.reserve_amount(balance, amount):
            raise InsufficientBalanceError("Insufficient balance")

        payment = await self.payment_repo.create(
            merchant_id=merchant_id,
            external_invoice_id=external_invoice_id,
            amount=amount,
        )

        await self.session.commit()

        try:
            from app.main import app as fastapi_app

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=fastapi_app),
                base_url="http://testserver",
            ) as client:
                provider_request = ProviderPaymentRequest(
                    payment_id=str(payment.id),
                    amount=amount,
                    callback_url="/api/v1/webhooks/provider",
                )
                response = await client.post(
                    "/provider/api/v1/payments",
                    json=provider_request.model_dump(mode="json"),
                    timeout=10.0,
                )
                response.raise_for_status()
                provider_data = response.json()

            await self.payment_repo.set_provider_payment_id(
                payment, provider_data["provider_payment_id"]
            )
            await self.payment_repo.update_status(payment, PaymentStatus.PROCESSING)
            await self.session.commit()

        except Exception as e:
            await self.payment_repo.update_status(
                payment, PaymentStatus.FAILED, failure_reason=str(e)
            )

            balance = await self.balance_repo.get_by_merchant_id_for_update(merchant_id)
            await self.balance_repo.release_reservation(balance, amount)
            await self.session.commit()
            raise

        return payment

    async def get_payment(self, payment_id: UUID) -> Optional[Payment]:
        return await self.payment_repo.get_by_id(payment_id)
