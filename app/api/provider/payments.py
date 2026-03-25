from fastapi import APIRouter

from app.schemas.payment import ProviderPaymentRequest, ProviderPaymentResponse
from app.services.provider_service import ProviderService

router = APIRouter()
provider_service = ProviderService()


@router.post("/payments", response_model=ProviderPaymentResponse, status_code=201)
async def create_provider_payment(payment_request: ProviderPaymentRequest):
    result = await provider_service.create_payment(
        payment_id=payment_request.payment_id,
        amount=payment_request.amount,
        callback_url=payment_request.callback_url,
    )
    return ProviderPaymentResponse(**result)
