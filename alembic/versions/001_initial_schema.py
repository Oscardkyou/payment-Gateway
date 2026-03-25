"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-03-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('merchants',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('api_token', sa.String(), nullable=False),
    sa.Column('secret_key', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_merchants_api_token'), 'merchants', ['api_token'], unique=True)

    op.create_table('balances',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('reserved_amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('merchant_id')
    )

    op.create_table('payments',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('external_invoice_id', sa.String(), nullable=False),
    sa.Column('provider_payment_id', sa.String(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'SUCCESS', 'CANCELED', 'FAILED', name='paymentstatus'), nullable=False),
    sa.Column('provider_status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELED', name='providerstatus'), nullable=True),
    sa.Column('failure_reason', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_external_invoice_id'), 'payments', ['external_invoice_id'], unique=False)
    op.create_index(op.f('ix_payments_provider_payment_id'), 'payments', ['provider_payment_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payments_provider_payment_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_external_invoice_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_table('balances')
    op.drop_index(op.f('ix_merchants_api_token'), table_name='merchants')
    op.drop_table('merchants')
    op.execute('DROP TYPE paymentstatus')
    op.execute('DROP TYPE providerstatus')
