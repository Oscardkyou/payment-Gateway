from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant


class MerchantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, merchant_id: UUID) -> Optional[Merchant]:
        result = await self.session.execute(
            select(Merchant).where(Merchant.id == merchant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_api_token(self, api_token: str) -> Optional[Merchant]:
        result = await self.session.execute(
            select(Merchant).where(Merchant.api_token == api_token)
        )
        return result.scalar_one_or_none()
