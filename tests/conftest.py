import asyncio
import os
from decimal import Decimal
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.sql import Executable
from httpx import AsyncClient
import redis.asyncio as redis

from app.core.database import Base
from app.main import app
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.merchant import Merchant
from app.models.balance import Balance
from app.api.provider.payments import provider_service


TEST_DATABASE_HOST = os.getenv("TEST_DATABASE_HOST", "db")
TEST_DATABASE_PORT = os.getenv("TEST_DATABASE_PORT", "5432")
TEST_REDIS_HOST = os.getenv("TEST_REDIS_HOST", "redis")
TEST_REDIS_PORT = os.getenv("TEST_REDIS_PORT", "6379")

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    f"postgresql+asyncpg://postgres:postgres@{TEST_DATABASE_HOST}:{TEST_DATABASE_PORT}/payment_gateway_test",
)
TEST_REDIS_URL = os.getenv(
    "TEST_REDIS_URL",
    f"redis://{TEST_REDIS_HOST}:{TEST_REDIS_PORT}/1",
)

ADMIN_DATABASE_URL = os.getenv(
    "TEST_ADMIN_DATABASE_URL",
    f"postgresql+psycopg2://postgres:postgres@{TEST_DATABASE_HOST}:{TEST_DATABASE_PORT}/postgres",
)

admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


class FreshReadAsyncSession(AsyncSession):
    async def execute(self, statement: Executable, *args, **kwargs):
        if hasattr(statement, "execution_options"):
            statement = statement.execution_options(populate_existing=True)
        return await super().execute(statement, *args, **kwargs)


request_async_session_maker = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)
assert_async_session_maker = async_sessionmaker(
    test_engine, class_=FreshReadAsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database() -> None:
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'payment_gateway_test'")
        ).scalar_one_or_none()

        if not exists:
            connection.execute(text("CREATE DATABASE payment_gateway_test"))
@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with assert_async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def test_merchant(db_session: AsyncSession) -> Merchant:
    merchant = Merchant(
        api_token="test-token",
        secret_key="super-secret-key",
    )
    db_session.add(merchant)
    await db_session.flush()

    balance = Balance(
        merchant_id=merchant.id,
        total_amount=Decimal("1000.00"),
        reserved_amount=Decimal("0.00"),
    )
    db_session.add(balance)

    await db_session.commit()
    await db_session.refresh(merchant)
    return merchant


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, redis_client: redis.Redis) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        async with request_async_session_maker() as session:
            yield session

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    await provider_service.wait_for_pending_webhooks()

    app.dependency_overrides.clear()
