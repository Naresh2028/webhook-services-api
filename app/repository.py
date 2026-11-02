from app.schemas import WebhookPayload
from app.database import get_session
from app.models import Transaction, PENDING, PROCESSING, PROCESSED, FAILED
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from app.models import utcnow
from datetime import timedelta
from app import config
from sqlalchemy import select, or_, and_

def create_if_new(payload:WebhookPayload) -> bool:
    
    with get_session() as session:
        session.add(
            Transaction(
                transaction_id = payload.transaction_id,
                source_account = payload.source_account,
                destination_account = payload.destination_account,
                amount = payload.amount,
                currency = payload.currency,
                status = PENDING
            )
        )
        
        try:
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False
        
def get_transaction(transaction_id:str) -> Optional[Transaction]:
    
    with get_session() as session:
        return session.get(Transaction, transaction_id)
    

def claim_pending(limit:int) -> List[str]:
    
    now = utcnow()
    stale_before = now - timedelta(seconds=config.STALE_LOCK_SECONDS)
    
    with get_session() as session:
        stmt = (
            select(Transaction)
            .where(
                Transaction.attempts < config.MAX_ATTEMPTS,
                or_ (
                    Transaction.status == PENDING,
                    and_ (Transaction.status == PROCESSING, Transaction.locked_at < stale_before)
                )
            )
            .order_by(Transaction.created_at)
            .limit(limit=limit)
            .with_for_update(skip_locked=True)
        )
        rows = session.execute(stmt).scalars().all()
        for row in rows:
            row.status = PROCESSING
            row.locked_at = now
            row.attempts += 1
        session.commit()
        return [row.transaction_id for row in rows]


def mark_processed(transaction_id:str) -> None:
    with get_session() as session:
        row = session.get(Transaction, transaction_id)
        
        if row is None or row.status == PROCESSED:
            return
        row.status = PROCESSED
        row.processed_at = utcnow()
        row.last_error = None
        row.locked_at = None
        session.commit()
        
def release_for_retry(transaction_id:str, error:str) -> None :
    
    with get_session() as session:
        row = session.get(Transaction,transaction_id)
        
        if row is None or row.status == PROCESSED:
            return 
        
        row.status = FAILED
        row.last_error = error[:1000]
        row.locked_at = None
        session.commit()