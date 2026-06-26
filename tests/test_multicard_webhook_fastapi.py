"""FastAPI Multicard success-callback webhook tests."""
import json
from hashlib import md5

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from starlette.requests import Request  # noqa: E402

from tolov.integrations.fastapi.models import PaymentTransaction, run_migrations  # noqa: E402
from tolov.integrations.fastapi.routes import MulticardWebhookHandler  # noqa: E402

SECRET = "testsecret"


def cb(store_id=105, invoice="inv-1", amount=500000, uuid="u-1", secret=SECRET):
    body = {
        "store_id": store_id,
        "invoice_id": invoice,
        "amount": amount,
        "uuid": uuid,
        "card_token": "TKN",
        "card_pan": "8600**0000",
        "ps": "uzcard",
        "receipt_url": "https://r",
        "phone": "998901234567",
        "billing_id": None,
        "payment_time": "2026-06-26 19:59:59",
    }
    body["sign"] = md5(f"{store_id}{invoice}{amount}{secret}".encode()).hexdigest()
    return body


def make_request(body):
    raw = json.dumps(body).encode()

    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/wh",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
    }
    return Request(scope, receive)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    run_migrations(engine)
    return sessionmaker(bind=engine)()


async def test_valid_signature_marks_paid(db):
    handler = MulticardWebhookHandler(db=db, secret=SECRET, account_model=None)
    resp = await handler.handle_webhook(make_request(cb(uuid="fa-ok")))
    assert resp.status_code == 200
    tx = (
        db.query(PaymentTransaction)
        .filter_by(gateway="multicard", transaction_id="fa-ok")
        .first()
    )
    assert tx.state == PaymentTransaction.SUCCESSFULLY
    assert float(tx.amount) == 5000.0
    assert tx.extra_data["card_token"] == "TKN"


async def test_bad_signature_rejected(db):
    handler = MulticardWebhookHandler(db=db, secret=SECRET, account_model=None)
    body = cb(uuid="fa-bad")
    body["sign"] = "deadbeef"
    resp = await handler.handle_webhook(make_request(body))
    assert resp.status_code == 403


def test_missing_secret_fails_closed(db):
    with pytest.raises(ValueError):
        MulticardWebhookHandler(db=db, secret="", account_model=None)


async def test_store_mismatch_rejected(db):
    handler = MulticardWebhookHandler(
        db=db, secret=SECRET, account_model=None, store_id=999
    )
    resp = await handler.handle_webhook(make_request(cb(store_id=105, uuid="fa-store")))
    assert resp.status_code == 403


async def test_idempotent(db):
    handler = MulticardWebhookHandler(db=db, secret=SECRET, account_model=None)
    await handler.handle_webhook(make_request(cb(uuid="fa-idem")))
    await handler.handle_webhook(make_request(cb(uuid="fa-idem")))
    count = (
        db.query(PaymentTransaction).filter_by(transaction_id="fa-idem").count()
    )
    assert count == 1
