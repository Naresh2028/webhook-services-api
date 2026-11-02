import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def make_payload(txn_id=None):
    return {
        "transaction_id": txn_id or f"txn_{uuid.uuid4().hex[:12]}",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR",
    }


def wait_for_status(client, txn_id, wanted=None, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        response = client.get(f"/v1/transactions/{txn_id}")
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            if data[0].get("processed_at") is not None:
                return data[0]
                
        time.sleep(0.2)
    raise AssertionError(f"{txn_id} never reached {wanted}. Last response was: {data}")



def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "HEALTHY"


def test_webhook_is_fast_and_returns_202(client):
    start = time.perf_counter()
    r = client.post("/v1/webhooks/transactions", json=make_payload())
    elapsed = time.perf_counter() - start
    assert r.status_code == 202
    assert elapsed < 0.5


def test_single_transaction_gets_processed(client):
    payload = make_payload()
    client.post("/v1/webhooks/transactions", json=payload)

    first = client.get(f"/v1/transactions/{payload['transaction_id']}").json()[0]
    assert first["transaction_id"] == payload["transaction_id"]
    assert first["processed_at"] is None

    done = wait_for_status(client, payload["transaction_id"], "PROCESSED")
    assert done["processed_at"] is not None

def test_duplicates_create_only_one_transaction(client):
    payload = make_payload()
    results = [client.post("/v1/webhooks/transactions", json=payload) for _ in range(5)]
    assert all(r.status_code == 202 for r in results)
    assert [r.json()["duplicate"] for r in results] == [False, True, True, True, True]

    wait_for_status(client, payload["transaction_id"], "PROCESSED")
    data = client.get(f"/v1/transactions/{payload['transaction_id']}").json()
    assert len(data) == 1

    from app import repository
    txn = repository.get_transaction(payload["transaction_id"])
    
    assert txn is not None, "Transaction was not found in the database!"
    assert txn.attempts == 1  



def test_unknown_transaction_is_404(client):
    assert client.get("/v1/transactions/does_not_exist").status_code == 404


def test_invalid_body_is_rejected(client):
    bad = make_payload()
    bad["amount"] = -5
    assert client.post("/v1/webhooks/transactions", json=bad).status_code == 422