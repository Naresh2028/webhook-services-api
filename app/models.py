from datetime import datetime, timezone
from app.database import Base
from sqlalchemy import String, Float, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Possible Status of Transactions
PENDING = "PENDING"
PROCESSING = "PROCESSING"
PROCESSED =  "PROCESSED"
FAILED = "FAILED"

class Transaction(Base):
    __tablename__ = "transactions";
    
    transaction_id : Mapped[str] = mapped_column(String(70), primary_key=True)
    
    source_account: Mapped[str] = mapped_column(String(80))
    destination_account: Mapped[str] = mapped_column(String(60))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(5))
    
    status: Mapped[str] = mapped_column(String(20), default=PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    
    attempts: Mapped[int] = mapped_column(Integer, default=0) # To find how many tries
    
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)