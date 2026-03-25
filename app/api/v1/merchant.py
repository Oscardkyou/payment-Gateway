from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import verify_api_token
from app.core.database import get_db
from app.models.merchant import Merchant
from app.repositories.balance_repository import BalanceRepository
from app.schemas.merchant import MerchantInfoResponse

router = APIRouter()


@router.get("/me", response_model=MerchantInfoResponse)
async def get_merchant_info(
    merchant: Merchant = Depends(verify_api_token),
    db: AsyncSession = Depends(get_db),
):
    balance_repo = BalanceRepository(db)
    balance = await balance_repo.get_by_merchant_id(merchant.id)

    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")

    available_amount = balance.total_amount - balance.reserved_amount

    return MerchantInfoResponse(
        id=merchant.id,
        total_amount=balance.total_amount,
        reserved_amount=balance.reserved_amount,
        available_amount=available_amount,
    )
