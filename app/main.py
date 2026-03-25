from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1 import payouts, merchant, webhooks
from app.api.provider import payments
from app.core.redis import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title="Payment Gateway API", version="1.0.0", lifespan=lifespan)

app.include_router(payouts.router, prefix="/api/v1", tags=["Payouts"])
app.include_router(merchant.router, prefix="/api/v1", tags=["Merchant"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(payments.router, prefix="/provider/api/v1", tags=["Provider"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
