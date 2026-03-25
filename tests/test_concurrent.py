import pytest
import asyncio
import hmac
import hashlib
import json
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.balance import Balance
from app.models.payment import Payment


def create_signature(body: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()


@pytest.mark.asyncio
async def test_concurrent_payouts_prevent_overspending(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    balance.total_amount = Decimal("100.00")
    balance.reserved_amount = Decimal("0.00")
    await db_session.commit()

    async def create_payout(invoice_id: str, amount: str):
        payload = {
            "external_invoice_id": invoice_id,
            "amount": amount
        }
        body = json.dumps(payload)
        signature = create_signature(body, test_merchant.secret_key)

        response = await client.post(
            "/api/v1/payouts",
            content=body,
            headers={
                "X-API-Token": test_merchant.api_token,
                "X-Signature": signature,
                "Content-Type": "application/json",
            },
        )
        return response

    results = await asyncio.gather(
        create_payout("concurrent-001", "80.00"),
        create_payout("concurrent-002", "80.00"),
        return_exceptions=True,
    )

    success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 201)
    failure_count = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 400)

    assert success_count == 1
    assert failure_count == 1

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    
    assert balance.total_amount == Decimal("100.00")
    assert balance.reserved_amount == Decimal("80.00")

    result = await db_session.execute(
        select(Payment).where(Payment.merchant_id == test_merchant.id)
    )
    payments = result.scalars().all()
    assert len(payments) == 1


@pytest.mark.asyncio
async def test_multiple_small_concurrent_payouts(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    balance.total_amount = Decimal("1000.00")
    balance.reserved_amount = Decimal("0.00")
    await db_session.commit()

    async def create_payout(invoice_id: str, amount: str):
        payload = {
            "external_invoice_id": invoice_id,
            "amount": amount
        }
        body = json.dumps(payload)
        signature = create_signature(body, test_merchant.secret_key)

        response = await client.post(
            "/api/v1/payouts",
            content=body,
            headers={
                "X-API-Token": test_merchant.api_token,
                "X-Signature": signature,
                "Content-Type": "application/json",
            },
        )
        return response

    tasks = [create_payout(f"small-{i:03d}", "50.00") for i in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 201)

    assert success_count == 10

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    
    assert balance.total_amount == Decimal("1000.00")
    assert balance.reserved_amount == Decimal("500.00")
