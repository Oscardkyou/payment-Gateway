import hmac
import hashlib
from typing import Optional
from fastapi import Header, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.merchant import Merchant
from app.repositories.merchant_repository import MerchantRepository


async def verify_api_token(
    x_api_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> Merchant:
    merchant_repo = MerchantRepository(db)
    merchant = await merchant_repo.get_by_api_token(x_api_token)
    
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API token")
    
    return merchant


async def verify_signature(
    request: Request,
    merchant: Merchant = Depends(verify_api_token),
    x_signature: Optional[str] = Header(None),
) -> Merchant:
    if not x_signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    body = await request.body()
    
    expected_signature = hmac.new(
        merchant.secret_key.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return merchant
