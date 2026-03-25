from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import verify_signature, verify_api_token
from app.core.database import get_db
from app.models.merchant import Merchant
from app.schemas.payment import PayoutRequest, PayoutResponse, PaymentDetailResponse
from app.services.payment_service import PaymentService, InsufficientBalanceError

router = APIRouter()


@router.post("/payouts", response_model=PayoutResponse, status_code=201)
async def create_payout(
    payout: PayoutRequest,
    merchant: Merchant = Depends(verify_signature),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    
    try:
        payment = await service.create_payout(
            merchant_id=merchant.id,
            external_invoice_id=payout.external_invoice_id,
            amount=payout.amount,
            provider_url="http://app:8000/provider/api/v1/payments",
        )
        return PayoutResponse.model_validate(payment)
    except InsufficientBalanceError:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payouts/{payment_id}", response_model=PaymentDetailResponse)
async def get_payout(
    payment_id: UUID,
    merchant: Merchant = Depends(verify_api_token),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    payment = await service.get_payment(payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.merchant_id != merchant.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return PaymentDetailResponse.model_validate(payment)
