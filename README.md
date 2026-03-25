# Payment Gateway Backend

A production-ready payment gateway backend service built with Python, FastAPI, PostgreSQL, and Redis. This service handles merchant payouts, integrates with a mock payment provider, processes webhooks, and ensures safe concurrent balance operations.

## Tech Stack

- **Python 3.12+**
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.x** - Async ORM with transaction support
- **Alembic** - Database migrations
- **PostgreSQL** - Primary database with row-level locking
- **Redis** - Webhook deduplication and caching
- **pytest** - Comprehensive test suite
- **Docker & Docker Compose** - Containerized deployment

## Features

### Core Functionality
- ✅ Merchant payout creation with balance reservation
- ✅ Mock payment provider integration
- ✅ Asynchronous webhook processing
- ✅ HMAC-SHA256 request signature validation
- ✅ Idempotent webhook handling with Redis
- ✅ Concurrent request safety with PostgreSQL row locking
- ✅ Proper balance management (total_amount, reserved_amount)

### Security
- API token authentication
- HMAC signature verification using `compare_digest`
- No secrets in code or logs
- Proper error handling without information leakage

### Data Integrity
- Transactional balance operations
- `SELECT ... FOR UPDATE` row locking to prevent race conditions
- Decimal precision for monetary values
- Idempotency keys for webhook deduplication

## Project Structure

```
payment-gateway/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── payouts.py       # Merchant payout endpoints
│   │   │   ├── merchant.py      # Merchant info endpoint
│   │   │   └── webhooks.py      # Provider webhook handler
│   │   ├── provider/
│   │   │   └── payments.py      # Mock provider API
│   │   └── dependencies.py      # Auth & signature verification
│   ├── core/
│   │   ├── config.py            # Application settings
│   │   ├── database.py          # Database connection
│   │   └── redis.py             # Redis connection
│   ├── models/
│   │   ├── merchant.py          # Merchant model
│   │   ├── balance.py           # Balance model
│   │   └── payment.py           # Payment model
│   ├── repositories/
│   │   ├── merchant_repository.py
│   │   ├── balance_repository.py
│   │   └── payment_repository.py
│   ├── schemas/
│   │   ├── payment.py           # Pydantic schemas
│   │   └── merchant.py
│   ├── services/
│   │   ├── payment_service.py   # Business logic
│   │   ├── webhook_service.py   # Webhook processing
│   │   └── provider_service.py  # Mock provider
│   └── main.py                  # FastAPI application
├── alembic/
│   └── versions/
│       ├── 001_initial_schema.py
│       └── 002_seed_test_data.py
├── tests/
│   ├── conftest.py              # Test fixtures
│   ├── test_payouts.py          # Payout tests
│   ├── test_webhooks.py         # Webhook tests
│   ├── test_concurrent.py       # Concurrency tests
│   └── test_merchant.py         # Merchant info tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)

### Running with Docker Compose

1. **Clone and navigate to the project:**
   ```bash
   cd payment-gateway
   ```

2. **Start all services:**
   ```bash
   docker-compose up --build
   ```

   This will:
   - Start PostgreSQL on port 5432
   - Start Redis on port 6379
   - Start the FastAPI app on port 8000
   - Run Alembic migrations automatically
   - Seed test data

3. **Verify the service is running:**
   ```bash
   curl http://localhost:8000/health
   ```

### Running Tests

#### With Docker (Recommended)

1. **Ensure PostgreSQL and Redis are running:**
   ```bash
   docker-compose up -d db redis
   ```

2. **Create test database:**
   ```bash
   docker-compose exec db psql -U postgres -c "CREATE DATABASE payment_gateway_test;"
   ```

3. **Run tests in container:**
   ```bash
   docker-compose exec app pytest -v
   ```

#### Locally (with virtual environment)

1. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure PostgreSQL and Redis are running locally**

4. **Create test database:**
   ```bash
   psql -U postgres -c "CREATE DATABASE payment_gateway_test;"
   ```

5. **Run tests:**
   ```bash
   pytest -v
   ```

6. **Run tests with coverage:**
   ```bash
   pytest --cov=app --cov-report=html
   ```

## Test Credentials

The seed migration creates a test merchant with the following credentials:

- **API Token:** `test-token`
- **Secret Key:** `super-secret-key`
- **Initial Balance:** 1000.00
- **Reserved Amount:** 0.00

## API Endpoints

### Merchant API

#### Create Payout
```bash
POST /api/v1/payouts
Headers:
  X-API-Token: test-token
  X-Signature: <hmac-sha256-signature>
  Content-Type: application/json

Body:
{
  "external_invoice_id": "inv-001",
  "amount": "100.00"
}

Response (201):
{
  "id": "uuid",
  "external_invoice_id": "inv-001",
  "amount": "100.00",
  "status": "processing",
  "created_at": "2024-03-24T10:00:00"
}
```

**Signature Calculation:**
```python
import hmac
import hashlib
import json

body = json.dumps({"external_invoice_id": "inv-001", "amount": "100.00"})
secret_key = "super-secret-key"
signature = hmac.new(secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
```

#### Get Payout
```bash
GET /api/v1/payouts/{payment_id}
Headers:
  X-API-Token: test-token

Response (200):
{
  "id": "uuid",
  "external_invoice_id": "inv-001",
  "provider_payment_id": "prov_abc123",
  "amount": "100.00",
  "status": "success",
  "provider_status": "Completed",
  "failure_reason": null,
  "created_at": "2024-03-24T10:00:00",
  "updated_at": "2024-03-24T10:00:02"
}
```

#### Get Merchant Info
```bash
GET /api/v1/me
Headers:
  X-API-Token: test-token

Response (200):
{
  "id": "uuid",
  "total_amount": "1000.00",
  "reserved_amount": "100.00",
  "available_amount": "900.00"
}
```

### Provider API (Internal Mock)

#### Create Provider Payment
```bash
POST /provider/api/v1/payments

Body:
{
  "payment_id": "uuid",
  "amount": "100.00",
  "callback_url": "http://app:8000/api/v1/webhooks/provider"
}

Response (201):
{
  "provider_payment_id": "prov_abc123",
  "status": "Processing",
  "message": "Payment processing"
}
```

### Webhook API

#### Provider Webhook
```bash
POST /api/v1/webhooks/provider

Body:
{
  "provider_payment_id": "prov_abc123",
  "status": "Completed",  // or "Canceled"
  "failure_reason": null
}

Response (200):
{
  "status": "ok"
}
```

## Payment Flow

1. **Merchant creates payout:**
   - Request validated (signature, token)
   - Balance checked: `available = total_amount - reserved_amount`
   - If sufficient, amount is **reserved** (not deducted yet)
   - Payment created with status `PENDING`

2. **Payment sent to provider:**
   - HTTP request to mock provider API
   - Provider returns `provider_payment_id`
   - Payment status updated to `PROCESSING`

3. **Provider sends webhook (async, 1-2 sec delay):**
   - Webhook received at `/api/v1/webhooks/provider`
   - Idempotency check via Redis
   - Payment found by `provider_payment_id`

4. **Webhook processing:**
   - **If Completed:**
     - `reserved_amount -= payment.amount`
     - `total_amount -= payment.amount`
     - Payment status → `SUCCESS`
   
   - **If Canceled:**
     - `reserved_amount -= payment.amount`
     - `total_amount` unchanged (money returned)
     - Payment status → `CANCELED`

## Balance Management

### Why `reserved_amount`?

The `reserved_amount` field prevents double-spending during the payment processing window:

1. **Without reservation:** Money could be spent twice if multiple requests arrive before provider confirms
2. **With reservation:** Money is locked immediately, preventing overspending
3. **On completion:** Reserved amount is released and deducted from total
4. **On cancellation:** Reserved amount is released, total remains unchanged

### Concurrent Safety

PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) ensures:
- Only one transaction can modify a balance at a time
- Two concurrent requests for 80.00 with balance 100.00 → one succeeds, one fails
- No race conditions or overspending possible

## Test Coverage

### Test Scenarios

✅ **A. Successful payout creation**
- Payment created with `processing` status
- `reserved_amount` increased
- `total_amount` unchanged

✅ **B. Insufficient balance**
- Request rejected with 400 error
- `reserved_amount` unchanged
- No payment created

✅ **C. Completed webhook**
- Payment status → `success`
- `reserved_amount` decreased
- `total_amount` decreased

✅ **D. Canceled webhook**
- Payment status → `canceled`
- `reserved_amount` decreased
- `total_amount` unchanged

✅ **E. Idempotent webhook**
- Duplicate webhook doesn't change balance
- Payment status unchanged after first processing

✅ **F. Concurrent requests**
- Two requests for 80.00 with balance 100.00
- Only one succeeds
- No overspending occurs

## Manual Testing

### Test Successful Payout

```bash
# Calculate signature
BODY='{"external_invoice_id":"test-001","amount":"50.00"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "super-secret-key" | awk '{print $2}')

# Create payout
curl -X POST http://localhost:8000/api/v1/payouts \
  -H "X-API-Token: test-token" \
  -H "X-Signature: $SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

### Check Balance

```bash
curl -X GET http://localhost:8000/api/v1/me \
  -H "X-API-Token: test-token"
```

### Test Insufficient Balance

```bash
BODY='{"external_invoice_id":"test-002","amount":"5000.00"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "super-secret-key" | awk '{print $2}')

curl -X POST http://localhost:8000/api/v1/payouts \
  -H "X-API-Token: test-token" \
  -H "X-Signature: $SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

## Architecture Decisions

### 1. **Repository Pattern**
Separates data access from business logic, making code testable and maintainable.

### 2. **Service Layer**
Contains business logic, transaction management, and external API calls.

### 3. **Row-Level Locking**
Uses `SELECT ... FOR UPDATE` to prevent concurrent balance modifications.

### 4. **Redis Deduplication**
Stores webhook processing keys with TTL to prevent duplicate processing.

### 5. **Decimal for Money**
Never uses `float` for monetary values to avoid precision errors.

### 6. **Async/Await**
Fully asynchronous for better performance under load.

### 7. **HMAC Signature**
Uses `compare_digest` to prevent timing attacks.

## Development

### Running Locally (without Docker)

1. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Start PostgreSQL and Redis:**
   ```bash
   # Using Homebrew on macOS
   brew services start postgresql@15
   brew services start redis
   ```

3. **Create database:**
   ```bash
   createdb payment_gateway
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start application:**
   ```bash
   uvicorn app.main:app --reload
   ```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Troubleshooting

### Port Already in Use
```bash
# Stop existing services
docker-compose down

# Or change ports in docker-compose.yml
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps db

# View logs
docker-compose logs db
```

### Test Database Issues
```bash
# Recreate test database
docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS payment_gateway_test;"
docker-compose exec db psql -U postgres -c "CREATE DATABASE payment_gateway_test;"
```

## Production Considerations

For production deployment, consider:

1. **Environment Variables:** Use proper secret management (AWS Secrets Manager, Vault)
2. **Database:** Connection pooling, read replicas, backups
3. **Redis:** Persistence, clustering, failover
4. **Monitoring:** Prometheus metrics, structured logging
5. **Rate Limiting:** Protect against abuse
6. **Webhook Retries:** Implement retry logic with exponential backoff
7. **Dead Letter Queue:** Handle failed webhooks
8. **API Versioning:** Maintain backward compatibility
9. **HTTPS:** TLS termination at load balancer
10. **Health Checks:** Liveness and readiness probes

## License

This is a test project for demonstration purposes.
