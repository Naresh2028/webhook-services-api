# Transaction Webhook Service

A Python service that receives transaction webhooks from payment processors (like Razorpay), acknowledges them immediately with `202 Accepted`, and processes them reliably in the background.

**Live API:** https://webhook-services-api.onrender.com

## Features

- Responds to webhooks in milliseconds (well under 500 ms), regardless of processing time
- Background processing with a 30-second simulated external call
- Idempotent: the same `transaction_id` is processed only once, however many times it is sent
- Persistent storage in PostgreSQL; no transaction is lost if the server restarts
- Automatic retries (up to 5 attempts) and recovery of transactions interrupted by a crash
- Automated tests

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check: `{"status": "HEALTHY", "current_time": "..."}` |
| `POST` | `/v1/webhooks/transactions` | Receive a webhook. Returns `202 Accepted` |
| `GET` | `/v1/transactions/{transaction_id}` | Get a transaction's status (returns a list; `404` if unknown) |

Webhook request body:

```json
{
  "transaction_id": "txn_abc123def456",
  "source_account": "acc_user_789",
  "destination_account": "acc_merchant_456",
  "amount": 1500,
  "currency": "INR"
}
```

Webhook response:

```json
{ "status": "ACCEPTED", "transaction_id": "txn_abc123def456", "duplicate": false }
```

Status values: `PENDING` -> `PROCESSING` -> `PROCESSED` (or `FAILED` after 5 failed attempts). `processed_at` is `null` until processing finishes.

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv

# Mac / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The server starts at http://127.0.0.1:8000 and creates a local SQLite file (`transactions.db`) automatically. To use PostgreSQL instead, set the `DATABASE_URL` environment variable.

## Test the service

### Automated tests

```bash
pytest -v
```

The tests use a temporary database and a 1-second delay instead of 30. They cover: health check, `202` in under 500 ms, a transaction reaching `PROCESSED`, duplicate prevention (5 identical webhooks -> 1 transaction, processed once), `404` for unknown ids, and `422` for invalid input.

### Manual test

Use `curl.exe` instead of `curl` on Windows PowerShell, or use the `/docs` page in a browser. Replace the base URL with the live URL when testing the deployment.

```bash
# 1. Health check
curl http://127.0.0.1:8000/

# 2. Send a webhook -> 202 immediately
curl -i -X POST http://127.0.0.1:8000/v1/webhooks/transactions \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"txn_abc123def456","source_account":"acc_user_789","destination_account":"acc_merchant_456","amount":1500,"currency":"INR"}'

# 3. Check status right away -> PENDING/PROCESSING, processed_at null
curl http://127.0.0.1:8000/v1/transactions/txn_abc123def456

# 4. Wait about 30 seconds and check again -> PROCESSED, processed_at filled in
curl http://127.0.0.1:8000/v1/transactions/txn_abc123def456

```

## Technical choices

**FastAPI.** Fast, with request validation built in (Pydantic) and automatic interactive docs at `/docs`. Invalid payloads are rejected with `422` without hand-written checks.

**PostgreSQL (Neon) as storage and as the work queue.** Each webhook is saved as a `PENDING` row *before* the `202` is returned, so a restart or crash can never lose a transaction. The worker picks up pending rows from the database. For this scope that avoids extra infrastructure (Redis, Celery, a message broker) while staying durable. SQLite is used only for local development and tests.

**Idempotency through the primary key.** `transaction_id` is the table's primary key. A duplicate insert fails at the database level, which the service catches and answers with a normal `202` (`"duplicate": true`). Because the database decides, this is safe even when two identical webhooks arrive at the same instant, which a "check, then insert" approach would not guarantee. Duplicates return `202` rather than an error because payment processors retry webhooks, and an error response would only trigger more retries.

**asyncio background worker.** A worker task runs inside the application, polls for `PENDING` rows every second, and processes each one with `asyncio.sleep(30)` standing in for slow external API calls. The sleeping is non-blocking, so thousands of transactions can wait their 30 seconds concurrently without extra threads, and webhook responses stay fast under load. Blocking database calls run in helper threads so the event loop is never stalled.

**Reliability.** Each row tracks `status`, `attempts`, `locked_at` and `last_error`.
- If processing raises an error, the row returns to `PENDING` and is retried; after 5 attempts it becomes `FAILED` with the error recorded.
- If the server dies mid-processing, the row stays `PROCESSING`; once its lock is older than 120 seconds it is claimed again.
- Rows are claimed with `SELECT ... FOR UPDATE SKIP LOCKED`, so several instances of the service can run side by side without processing the same transaction twice.
- The worker loop catches and logs errors (for example a brief database outage) and keeps running.

**Layered code structure.** `main.py` (HTTP layer), `repository.py` (all database access), `worker.py` (background processing), `models.py` / `schemas.py` (data shapes) and `config.py` (settings from environment variables) each have one job, which keeps the code easy to read and test.

## Project structure

```
app/
  config.py        settings from environment variables
  database.py      engine, sessions, table creation
  models.py        Transaction table
  schemas.py       request/response validation
  repository.py    database operations (save, read, claim, finish, retry)
  worker.py        background processor
  main.py          API endpoints
tests/
  conftest.py      test setup (temporary DB, short delay)
  test_api.py      automated tests
requirements.txt
requirements-dev.txt
render.yaml        Render deployment settings
.env.example       example environment variables
```

## Deployment

Deployed on **Render** (web service) with a **Neon** PostgreSQL database.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables: `DATABASE_URL` (Neon connection string), `PYTHON_VERSION=3.12.3`
- Health check path: `/`

## Limitations and next steps

- The worker runs inside the web process. This is simple and fine at this scale; for heavier load I would move it into its own service or use a dedicated queue (SQS, or Redis with Celery/Arq).
- Add structured logging, metrics and alerting, and a review workflow for `FAILED` transactions.
- Use database migrations (Alembic) instead of creating tables at startup.
