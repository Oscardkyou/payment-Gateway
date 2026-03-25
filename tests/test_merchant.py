import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.balance import Balance


@pytest.mark.asyncio
async def test_get_merchant_info(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    response = await client.get(
        "/api/v1/me",
        headers={"X-API-Token": test_merchant.api_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["total_amount"]) == Decimal("1000.00")
    assert Decimal(data["reserved_amount"]) == Decimal("0.00")
    assert Decimal(data["available_amount"]) == Decimal("1000.00")


@pytest.mark.asyncio
async def test_get_merchant_info_with_reserved(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    balance.reserved_amount = Decimal("300.00")
    await db_session.commit()

    response = await client.get(
        "/api/v1/me",
        headers={"X-API-Token": test_merchant.api_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["total_amount"]) == Decimal("1000.00")
    assert Decimal(data["reserved_amount"]) == Decimal("300.00")
    assert Decimal(data["available_amount"]) == Decimal("700.00")


@pytest.mark.asyncio
async def test_get_merchant_info_unauthorized(client: AsyncClient):
    response = await client.get(
        "/api/v1/me",
        headers={"X-API-Token": "invalid-token"},
    )

    assert response.status_code == 401
