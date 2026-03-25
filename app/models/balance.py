import uuid
from decimal import Decimal
from sqlalchemy import Column, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Balance(Base):
    __tablename__ = "balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), unique=True, nullable=False)
    total_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=Decimal("0.00"))
    reserved_amount = Column(Numeric(precision=15, scale=2), nullable=False, default=Decimal("0.00"))
    
    merchant = relationship("Merchant", back_populates="balance")
