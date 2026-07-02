"""Async FastAPI webhook handler tests (SQLAlchemy AsyncSession / aiosqlite).

Mirrors tests/test_multicard_webhook_fastapi.py but exercises the async handlers
in tolov.integrations.fastapi.aio, focusing on: signature/auth accept+reject,
mark-as-paid, and the exactly-once hook firing under retried callbacks.
"""
import base64
import json
from hashlib import md5
from urllib.parse import urlencode

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy import Column, Float, Integer, select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402
from starlette.requests import Request  # noqa: E402

from tolov.integrations.fastapi.models import (  # noqa: E402
    Base,
    PaymentTransaction,
    run_migrations_async,
)
from tolov.integrations.fastapi.aio import (  # noqa: E402
    PaymeWebhookHandler,
    ClickWebhookHandler,
    MulticardWebhookHandler,
)

PAYME_KEY = "payme-secret-key"
CLICK_SERVICE_ID = "12345"
CLICK_SECRET = "click-secret"
MULTICARD_SECRET = "mc-secret"


class Order(Base):
    """Minimal account model for the async webhook tests."""

    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    amount = Column(Float)


@pytest.fixture
async def db():
    """Fresh in-memory async DB per test; disposes the engine on teardown."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await run_migrations_async(engine)
    session = async_sessionmaker(engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


# --------------------------------------------------------------------------
# request builders + signing helpers
# --------------------------------------------------------------------------


def _request(body: bytes, headers):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/wh",
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope, receive)


def json_request(obj, auth=None):
    headers = [(b"content-type", b"application/json")]
    if auth:
        headers.append((b"authorization", auth.encode()))
    return _request(json.dumps(obj).encode(), headers)


def form_request(params):
    body = urlencode(params).encode()
    return _request(body, [(b"content-type", b"application/x-www-form-urlencoded")])


def payme_auth(key=PAYME_KEY, user="Paycom"):
    return "Basic " + base64.b64encode(f"{user}:{key}".encode()).decode()


def click_sign(params, secret=CLICK_SECRET):
    parts = [
        str(params.get("click_trans_id") or ""),
        str(params.get("service_id") or ""),
        str(secret or ""),
        str(params.get("merchant_trans_id") or ""),
        str(params.get("merchant_prepare_id") or ""),
        str(params.get("amount") or ""),
        str(params.get("action") or ""),
        str(params.get("sign_time")),
    ]
    return md5("".join(parts).encode()).hexdigest()


def mc_body(
    store_id=105, invoice="inv-1", amount=500000, uuid="mc-1", secret=MULTICARD_SECRET
):
    body = {
        "store_id": store_id,
        "invoice_id": invoice,
        "amount": amount,
        "uuid": uuid,
        "card_token": "TKN",
        "card_pan": "8600**0000",
        "ps": "uzcard",
        "payment_time": "2026-06-26 19:59:59",
    }
    body["sign"] = md5(f"{store_id}{invoice}{amount}{secret}".encode()).hexdigest()
    return body


async def seed_order(db, order_id=1, amount=5000.0):
    order = Order(id=order_id, amount=amount)
    db.add(order)
    await db.commit()
    return order


async def get_tx(db, transaction_id):
    return (
        (
            await db.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.transaction_id == transaction_id
                )
            )
        )
        .scalars()
        .first()
    )


async def count_tx(db, transaction_id):
    rows = (
        (
            await db.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.transaction_id == transaction_id
                )
            )
        )
        .scalars()
        .all()
    )
    return len(rows)


def body_json(response):
    return json.loads(response.body)


# --------------------------------------------------------------------------
# Multicard
# --------------------------------------------------------------------------


async def test_multicard_valid_signature_marks_paid(db):
    handler = MulticardWebhookHandler(
        db=db, secret=MULTICARD_SECRET, account_model=None
    )
    resp = await handler.handle_webhook(json_request(mc_body(uuid="mc-ok")))
    assert resp.status_code == 200
    tx = await get_tx(db, "mc-ok")
    assert tx.state == PaymentTransaction.SUCCESSFULLY
    assert float(tx.amount) == 5000.0
    assert tx.extra_data["card_token"] == "TKN"


async def test_multicard_bad_signature_rejected(db):
    handler = MulticardWebhookHandler(
        db=db, secret=MULTICARD_SECRET, account_model=None
    )
    body = mc_body(uuid="mc-bad")
    body["sign"] = "deadbeef"
    resp = await handler.handle_webhook(json_request(body))
    assert resp.status_code == 403
    assert await count_tx(db, "mc-bad") == 0


def test_multicard_missing_secret_fails_closed():
    with pytest.raises(ValueError):
        MulticardWebhookHandler(db=None, secret="", account_model=None)


async def test_multicard_store_mismatch_rejected(db):
    handler = MulticardWebhookHandler(
        db=db, secret=MULTICARD_SECRET, account_model=None, store_id=999
    )
    resp = await handler.handle_webhook(
        json_request(mc_body(store_id=105, uuid="mc-store"))
    )
    assert resp.status_code == 403


async def test_multicard_idempotent_hook_fires_once(db):
    calls = {"n": 0}

    class H(MulticardWebhookHandler):
        def successfully_payment(self, params, transaction):
            calls["n"] += 1

    handler = H(db=db, secret=MULTICARD_SECRET, account_model=None)
    await handler.handle_webhook(json_request(mc_body(uuid="mc-idem")))
    await handler.handle_webhook(json_request(mc_body(uuid="mc-idem")))  # retry
    tx = await get_tx(db, "mc-idem")
    assert await count_tx(db, "mc-idem") == 1
    assert tx.state == PaymentTransaction.SUCCESSFULLY
    assert calls["n"] == 1


# --------------------------------------------------------------------------
# Payme
# --------------------------------------------------------------------------


def payme_handler(db, cls=PaymeWebhookHandler):
    return cls(
        db=db,
        payme_id="paycom",
        payme_key=PAYME_KEY,
        account_model=Order,
        account_field="order_id",
        amount_field="amount",
    )


async def test_payme_auth_failure_returns_permission_error(db):
    handler = payme_handler(db)
    req = json_request(
        {"method": "CheckPerformTransaction", "params": {}, "id": 1},
        auth=payme_auth(key="wrong-key"),
    )
    resp = await handler.handle_webhook(req)
    assert body_json(resp)["error"]["code"] == -32504


async def test_payme_check_perform_allows(db):
    await seed_order(db, order_id=1, amount=5000.0)
    handler = payme_handler(db)
    req = json_request(
        {
            "method": "CheckPerformTransaction",
            "params": {"account": {"order_id": "1"}, "amount": 500000},
            "id": 7,
        },
        auth=payme_auth(),
    )
    resp = await handler.handle_webhook(req)
    assert body_json(resp)["result"] == {"allow": True}


async def test_payme_create_then_perform_marks_paid_once(db):
    await seed_order(db, order_id=1, amount=5000.0)
    calls = {"n": 0}

    class H(PaymeWebhookHandler):
        def successfully_payment(self, params, transaction):
            calls["n"] += 1

    handler = payme_handler(db, cls=H)

    create = json_request(
        {
            "method": "CreateTransaction",
            "params": {
                "id": "pm-1",
                "account": {"order_id": "1"},
                "amount": 500000,
                "time": 123456,
            },
            "id": 1,
        },
        auth=payme_auth(),
    )
    created = body_json(await handler.handle_webhook(create))["result"]
    assert created["transaction"] == "pm-1"
    assert created["state"] == PaymentTransaction.INITIATING

    def perform_req():
        return json_request(
            {"method": "PerformTransaction", "params": {"id": "pm-1"}, "id": 2},
            auth=payme_auth(),
        )

    r1 = body_json(await handler.handle_webhook(perform_req()))["result"]
    await handler.handle_webhook(perform_req())  # provider retry
    assert r1["state"] == PaymentTransaction.SUCCESSFULLY
    assert calls["n"] == 1


async def test_payme_cancel_marks_cancelled_once(db):
    await seed_order(db, order_id=1, amount=5000.0)
    calls = {"n": 0}

    class H(PaymeWebhookHandler):
        def cancelled_payment(self, params, transaction):
            calls["n"] += 1

    handler = payme_handler(db, cls=H)
    await handler.handle_webhook(
        json_request(
            {
                "method": "CreateTransaction",
                "params": {
                    "id": "pm-c",
                    "account": {"order_id": "1"},
                    "amount": 500000,
                    "time": 1,
                },
                "id": 1,
            },
            auth=payme_auth(),
        )
    )
    # Perform first, so cancel moves SUCCESSFULLY -> CANCELLED (-2) rather than
    # INITIATING -> CANCELLED_DURING_INIT (-1).
    await handler.handle_webhook(
        json_request(
            {"method": "PerformTransaction", "params": {"id": "pm-c"}, "id": 2},
            auth=payme_auth(),
        )
    )

    def cancel_req():
        return json_request(
            {
                "method": "CancelTransaction",
                "params": {"id": "pm-c", "reason": 5},
                "id": 3,
            },
            auth=payme_auth(),
        )

    r1 = body_json(await handler.handle_webhook(cancel_req()))["result"]
    await handler.handle_webhook(cancel_req())  # retry
    assert r1["state"] == PaymentTransaction.CANCELLED
    assert calls["n"] == 1


# --------------------------------------------------------------------------
# Click
# --------------------------------------------------------------------------


def click_handler(db, cls=ClickWebhookHandler):
    return cls(
        db=db,
        service_id=CLICK_SERVICE_ID,
        secret_key=CLICK_SECRET,
        account_model=Order,
        account_field="id",
    )


async def test_click_prepare_creates_transaction(db):
    await seed_order(db, order_id=1, amount=5000.0)
    handler = click_handler(db)

    params = {
        "click_trans_id": "cl-1",
        "service_id": CLICK_SERVICE_ID,
        "merchant_trans_id": "1",
        "merchant_prepare_id": "",
        "amount": "5000.0",
        "action": "0",
        "sign_time": "2026-07-02 10:00:00",
    }
    params["sign_string"] = click_sign(params)

    resp = await handler.handle_webhook(form_request(params))
    assert resp["error"] == 0
    tx = await get_tx(db, "cl-1")
    assert tx.state == PaymentTransaction.INITIATING


async def test_click_complete_marks_paid_once(db):
    await seed_order(db, order_id=1, amount=5000.0)
    calls = {"n": 0}

    class H(ClickWebhookHandler):
        def successfully_payment(self, params, transaction):
            calls["n"] += 1

    handler = click_handler(db, cls=H)

    params = {
        "click_trans_id": "cl-2",
        "service_id": CLICK_SERVICE_ID,
        "merchant_trans_id": "1",
        "merchant_prepare_id": "",
        "amount": "5000.0",
        "action": "1",
        "error": "0",
        "sign_time": "2026-07-02 10:00:00",
    }
    params["sign_string"] = click_sign(params)

    resp1 = await handler.handle_webhook(form_request(params))
    await handler.handle_webhook(form_request(params))  # retry
    assert resp1["error"] == 0
    tx = await get_tx(db, "cl-2")
    assert tx.state == PaymentTransaction.SUCCESSFULLY
    assert calls["n"] == 1


async def test_click_bad_signature_no_payment(db):
    await seed_order(db, order_id=1, amount=5000.0)
    handler = click_handler(db)

    params = {
        "click_trans_id": "cl-bad",
        "service_id": CLICK_SERVICE_ID,
        "merchant_trans_id": "1",
        "amount": "5000.0",
        "action": "1",
        "error": "0",
        "sign_time": "2026-07-02 10:00:00",
        "sign_string": "deadbeef",
    }

    resp = await handler.handle_webhook(form_request(params))
    assert resp["error"] != 0  # not a success response
    assert await count_tx(db, "cl-bad") == 0
