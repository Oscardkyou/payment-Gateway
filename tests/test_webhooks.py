import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.balance import Balance
from app.models.payment import Payment, PaymentStatus, ProviderStatus


@pytest.mark.asyncio
async def test_webhook_completed(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    payment = Payment(
        merchant_id=test_merchant.id,
        external_invoice_id="inv-webhook-001",
        provider_payment_id="prov-001",
        amount=Decimal("150.00"),
        status=PaymentStatus.PROCESSING,
    )
    db_session.add(payment)

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    balance.reserved_amount = Decimal("150.00")
    
    await db_session.commit()

    webhook_payload = {
        "provider_payment_id": "prov-001",
        "status": "Completed",
    }

    response = await client.post(
        "/api/v1/webhooks/provider",
        json=webhook_payload,
    )

    assert response.status_code == 200

    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.provider_status == ProviderStatus.COMPLETED

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    assert balance.reserved_amount == Decimal("0.00")
    assert balance.total_amount == Decimal("850.00")


@pytest.mark.asyncio
async def test_webhook_canceled(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    payment = Payment(
        merchant_id=test_merchant.id,
        external_invoice_id="inv-webhook-002",
        provider_payment_id="prov-002",
        amount=Decimal("100.00"),
        status=PaymentStatus.PROCESSING,
    )
    db_session.add(payment)

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    balance.reserved_amount = Decimal("100.00")
    
    await db_session.commit()

    webhook_payload = {
        "provider_payment_id": "prov-002",
        "status": "Canceled",
        "failure_reason": "Provider declined",
    }

    response = await client.post(
        "/api/v1/webhooks/provider",
        json=webhook_payload,
    )

    assert response.status_code == 200

    await db_session.refresh(payment)
    assert payment.status == PaymentStatus.CANCELED
    assert payment.provider_status == ProviderStatus.CANCELED
    assert payment.failure_reason == "Provider declined"

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    assert balance.reserved_amount == Decimal("0.00")
    assert balance.total_amount == Decimal("1000.00")


@pytest.mark.asyncio
async def test_webhook_idempotency(
    client: AsyncClient,
    test_merchant: Merchant,
    db_session: AsyncSession,
):
    payment = Payment(
        merchant_id=test_merchant.id,
        external_invoice_id="inv-webhook-003",
        provider_payment_id="prov-003",
        amount=Decimal("200.00"),
        status=PaymentStatus.PROCESSING,
    )
    db_session.add(payment)

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance = result.scalar_one()
    balance.reserved_amount = Decimal("200.00")
    
    await db_session.commit()

    webhook_payload = {
        "provider_payment_id": "prov-003",
        "status": "Completed",
    }

    response1 = await client.post(
        "/api/v1/webhooks/provider",
        json=webhook_payload,
    )
    assert response1.status_code == 200

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance_after_first = result.scalar_one()
    first_total = balance_after_first.total_amount
    first_reserved = balance_after_first.reserved_amount

    response2 = await client.post(
        "/api/v1/webhooks/provider",
        json=webhook_payload,
    )
    assert response2.status_code == 200

    result = await db_session.execute(
        select(Balance).where(Balance.merchant_id == test_merchant.id)
    )
    balance_after_second = result.scalar_one()
    
    assert balance_after_second.total_amount == first_total
    assert balance_after_second.reserved_amount == first_reserved


@pytest.mark.asyncio
async def test_webhook_payment_not_found(client: AsyncClient):
    webhook_payload = {
        "provider_payment_id": "non-existent",
        "status": "Completed",
    }

    response = await client.post(
        "/api/v1/webhooks/provider",
        json=webhook_payload,
    )

    assert response.status_code == 404
