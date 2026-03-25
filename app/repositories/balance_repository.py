from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.balance import Balance


class BalanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_merchant_id(self, merchant_id: UUID) -> Optional[Balance]:
        result = await self.session.execute(
            select(Balance).where(Balance.merchant_id == merchant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_merchant_id_for_update(self, merchant_id: UUID) -> Optional[Balance]:
        result = await self.session.execute(
            select(Balance)
            .where(Balance.merchant_id == merchant_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def reserve_amount(self, balance: Balance, amount: Decimal) -> bool:
        available = balance.total_amount - balance.reserved_amount
        if available < amount:
            return False
        
        balance.reserved_amount += amount
        return True

    async def release_reservation(self, balance: Balance, amount: Decimal) -> None:
        balance.reserved_amount -= amount

    async def complete_payment(self, balance: Balance, amount: Decimal) -> None:
        balance.reserved_amount -= amount
        balance.total_amount -= amount
