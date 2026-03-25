"""seed test data

Revision ID: 002
Revises: 001
Create Date: 2024-03-24 10:01:00.000000

"""
from alembic import op
import uuid

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    merchant_id = str(uuid.uuid4())
    
    op.execute(f"""
        INSERT INTO merchants (id, api_token, secret_key)
        VALUES ('{merchant_id}', 'test-token', 'super-secret-key')
    """)
    
    op.execute(f"""
        INSERT INTO balances (id, merchant_id, total_amount, reserved_amount)
        VALUES ('{uuid.uuid4()}', '{merchant_id}', 1000.00, 0.00)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM balances WHERE merchant_id IN (SELECT id FROM merchants WHERE api_token = 'test-token')")
    op.execute("DELETE FROM merchants WHERE api_token = 'test-token'")
