import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_token = Column(String, unique=True, nullable=False, index=True)
    secret_key = Column(String, nullable=False)
    
    balance = relationship("Balance", back_populates="merchant", uselist=False)
    payments = relationship("Payment", back_populates="merchant")
