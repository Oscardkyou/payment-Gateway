import pytest
import hmac
import hashlib
import json
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.balance import Balance
from app.models.payment import Payment, PaymentStatus


def create_signature(body: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()


@pytest.mark.asyncio
async def test_create_payout_success(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    payload = {
        "external_invoice_id": "inv-001",
        "amount": "100.00"
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

    assert response.status_code == 201
    data = response.json()
    assert data["external_invoice_id"] == "inv-001"
    assert Decimal(data["amount"]) == Decimal("100.00")
    assert data["status"] == "processing"

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    assert balance.reserved_amount == Decimal("100.00")
    assert balance.total_amount == Decimal("1000.00")


@pytest.mark.asyncio
async def test_create_payout_insufficient_balance(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    payload = {
        "external_invoice_id": "inv-002",
        "amount": "1500.00"
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

    assert response.status_code == 400
    assert "Insufficient balance" in response.json()["detail"]

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    assert balance.reserved_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_create_payout_invalid_signature(
    client: AsyncClient,
    test_merchant: Merchant,
):
    payload = {
        "external_invoice_id": "inv-003",
        "amount": "50.00"
    }
    body = json.dumps(payload)

    response = await client.post(
        "/api/v1/payouts",
        content=body,
        headers={
            "X-API-Token": test_merchant.api_token,
            "X-Signature": "invalid-signature",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_payout_missing_token(client: AsyncClient):
    payload = {
        "external_invoice_id": "inv-004",
        "amount": "50.00"
    }

    response = await client.post(
        "/api/v1/payouts",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_payout(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    payment = Payment(
        merchant_id=test_merchant.id,
        external_invoice_id="inv-005",
        amount=Decimal("200.00"),
        status=PaymentStatus.PROCESSING,
    )
    db_session.add(payment)
    await db_session.commit()
    await db_session.refresh(payment)

    response = await client.get(
        f"/api/v1/payouts/{payment.id}",
        headers={"X-API-Token": test_merchant.api_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["external_invoice_id"] == "inv-005"
    assert Decimal(data["amount"]) == Decimal("200.00")
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_get_payout_not_found(
    client: AsyncClient,
    test_merchant: Merchant,
):
    import uuid
    fake_id = uuid.uuid4()

    response = await client.get(
        f"/api/v1/payouts/{fake_id}",
        headers={"X-API-Token": test_merchant.api_token},
    )

    assert response.status_code == 404
