from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.payment import ProviderWebhookRequest
from app.services.webhook_service import WebhookService

router = APIRouter()


@router.post("/webhooks/provider", status_code=200)
async def handle_provider_webhook(
    webhook: ProviderWebhookRequest,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis),
):
    service = WebhookService(db, redis_client)
    
    try:
        await service.process_webhook(
            provider_payment_id=webhook.provider_payment_id,
            status=webhook.status,
            failure_reason=webhook.failure_reason,
        )
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
