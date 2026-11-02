import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, HTTPException
from app.database import init_db
import asyncio
from app.worker import worker_loop
from datetime import datetime, timezone
from app.schemas import WebhookPayload, TransactionOut
from app import repository
from typing import List


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s ")

@asynccontextmanager
async def lifespan(app:FastAPI):
    init_db()
    worker = asyncio.create_task(worker_loop())
    yield
    worker.cancel()
    try:
        await worker
    except asyncio.CancelledError:
        pass
    

app = FastAPI(title="Trasaction webhook service", lifespan=lifespan)


@app.get("/")
def health_check():
    return{
        "status":"HEALTHY",
        "current_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    
@app.post("/v1/webhooks/transactions", status_code=status.HTTP_202_ACCEPTED)
def receive_webhook(payload:WebhookPayload):
    
    is_new = repository.create_if_new(payload)
    return {
       "status":"Accepted",
        "transaction_id":payload.transaction_id,
        "duplicate": not is_new
    }
    
@app.get("/v1/transactions/{transaction_id}", response_model=List[TransactionOut])
def get_transaction(transaction_id:str):
        row = repository.get_transaction(transaction_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return [row]