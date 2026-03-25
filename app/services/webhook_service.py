from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.models.payment import PaymentStatus, ProviderStatus
from app.repositories.balance_repository import BalanceRepository
from app.repositories.payment_repository import PaymentRepository


class WebhookService:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.balance_repo = BalanceRepository(session)
        self.redis = redis_client

    async def process_webhook(
        self,
        provider_payment_id: str,
        status: ProviderStatus,
        failure_reason: str = None,
    ) -> None:
        dedup_key = f"webhook:{provider_payment_id}:{status.value}"
        
        if await self.redis.exists(dedup_key):
            return

        payment = await self.payment_repo.get_by_provider_payment_id(provider_payment_id)
        if not payment:
            raise ValueError("Payment not found")

        if payment.status in [PaymentStatus.SUCCESS, PaymentStatus.CANCELED]:
            return

        balance = await self.balance_repo.get_by_merchant_id_for_update(payment.merchant_id)
        if not balance:
            raise ValueError("Balance not found")

        if status == ProviderStatus.COMPLETED:
            await self.balance_repo.complete_payment(balance, payment.amount)
            await self.payment_repo.update_status(
                payment, PaymentStatus.SUCCESS, provider_status=status
            )
        elif status == ProviderStatus.CANCELED:
            await self.balance_repo.release_reservation(balance, payment.amount)
            await self.payment_repo.update_status(
                payment, PaymentStatus.CANCELED, provider_status=status, failure_reason=failure_reason
            )
        else:
            await self.payment_repo.update_status(
                payment, payment.status, provider_status=status
            )

        await self.redis.setex(dedup_key, 3600, "1")
        await self.session.commit()
