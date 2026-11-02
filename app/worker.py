import logging
import asyncio
from app import repository, config

logger = logging.getLogger("worker")

async def process_transaction(transaction_id:str) -> None:
    try:
        await asyncio.sleep(config.PROCESSING_DELAY_SECONDS)
        
        await asyncio.to_thread(repository.mark_processed, transaction_id)
        logger.info("Processed %s", transaction_id)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Failed to process %s", transaction_id)
        await asyncio.to_thread(repository.release_for_retry, transaction_id, repr(exc))

async def worker_loop() -> None:
    running = set()
    
    logger.info("Worker started")
    
    while True:
        try:
            ids = await asyncio.to_thread(repository.claim_pending, config.BATCH_SIZE)
            for transaction_id in ids:
                task = asyncio.create_task(process_transaction(transaction_id))
                running.add(task)
                task.add_done_callback(running.discard)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker could not fetch work; will retry")
            
        await asyncio.sleep(config.POOL_INTERVAL_SECONDS)