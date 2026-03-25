import asyncio
import uuid
import random
from decimal import Decimal
import httpx

from app.models.payment import ProviderStatus
from app.schemas.payment import ProviderWebhookRequest


class ProviderService:
    def __init__(self):
        self.payments = {}
        self._pending_webhook_tasks: set[asyncio.Task] = set()

    async def create_payment(
        self,
        payment_id: str,
        amount: Decimal,
        callback_url: str,
    ) -> dict:
        provider_payment_id = f"prov_{uuid.uuid4().hex[:16]}"

        self.payments[provider_payment_id] = {
            "payment_id": payment_id,
            "amount": amount,
            "callback_url": callback_url,
            "status": ProviderStatus.PROCESSING,
        }

        task = asyncio.create_task(self._send_webhook_delayed(provider_payment_id, callback_url))
        self._pending_webhook_tasks.add(task)
        task.add_done_callback(self._pending_webhook_tasks.discard)

        return {
            "provider_payment_id": provider_payment_id,
            "status": ProviderStatus.PROCESSING,
            "message": "Payment processing",
        }

    async def _send_webhook_delayed(self, provider_payment_id: str, callback_url: str):
        await asyncio.sleep(2)

        final_status = random.choice([ProviderStatus.COMPLETED, ProviderStatus.CANCELED])
        failure_reason = "Random cancellation" if final_status == ProviderStatus.CANCELED else None

        webhook_data = ProviderWebhookRequest(
            provider_payment_id=provider_payment_id,
            status=final_status,
            failure_reason=failure_reason,
        )

        try:
            from app.main import app as fastapi_app

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=fastapi_app),
                base_url="http://testserver",
            ) as client:
                await client.post(
                    callback_url or "/api/v1/webhooks/provider",
                    json=webhook_data.model_dump(mode="json"),
                    timeout=10.0,
                )
        except Exception:
            pass

    async def wait_for_pending_webhooks(self) -> None:
        if not self._pending_webhook_tasks:
            return

        tasks = list(self._pending_webhook_tasks)
        await asyncio.gather(*tasks, return_exceptions=True)

    def set_deterministic_status(self, status: ProviderStatus):
        self._deterministic_status = status

    async def _send_webhook_delayed_deterministic(
        self, provider_payment_id: str, callback_url: str, status: ProviderStatus
    ):
        await asyncio.sleep(0.1)

        failure_reason = "Test cancellation" if status == ProviderStatus.CANCELED else None

        webhook_data = ProviderWebhookRequest(
            provider_payment_id=provider_payment_id,
            status=status,
            failure_reason=failure_reason,
        )

        try:
            from app.main import app as fastapi_app

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=fastapi_app),
                base_url="http://testserver",
            ) as client:
                await client.post(
                    callback_url or "/api/v1/webhooks/provider",
                    json=webhook_data.model_dump(mode="json"),
                    timeout=10.0,
                )
        except Exception:
            pass
