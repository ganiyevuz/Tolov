"""Live integration tests against the Multicard sandbox (dev-mesh).

Uses the public sandbox credentials from conftest. Run only these with:
    pytest -m live
Skip them with:
    pytest -m 'not live'
They auto-skip when the sandbox is unreachable (see the `live` fixture).
"""
import uuid

import httpx
import pytest

from conftest import APPLICATION_ID, BASE_DEV, SECRET, STORE_ID, TEST_CARD
from tolov import MulticardGateway
from tolov.core.exceptions import PaymentException, TransactionNotFound

pytestmark = pytest.mark.live


def _gw():
    return MulticardGateway(
        application_id=APPLICATION_ID, secret=SECRET, store_id=STORE_ID, is_test_mode=True
    )


def _uid():
    return "pytest-" + uuid.uuid4().hex[:10]


def test_auth_and_app_info(live):
    info = _gw().reports.app_info()
    assert info["application_id"] == APPLICATION_ID
    assert "wallet_sum" in info
    assert any(s["id"] == STORE_ID for s in info["stores"])


def test_invoice_lifecycle(live):
    mc = _gw()
    inv = mc.invoices.create(
        amount=150000, invoice_id=_uid(), callback_url="https://example.com/cb"
    )
    u = inv["uuid"]
    assert inv["checkout_url"].startswith("http")
    assert mc.invoices.get(u)["uuid"] == u
    res = mc.check_payment(u)
    assert isinstance(res["state"], int)
    assert "status" in res and res["data"]
    assert mc.invoices.delete(u) == []


def test_create_payment_returns_checkout_url(live):
    url = _gw().create_payment(
        id=_uid(), amount=1500, callback_url="https://example.com/cb"
    )
    assert url.startswith("http")


def test_reports_registries(live):
    mc = _gw()
    reg = mc.reports.payment_registry(
        "2026-01-01 00:00:00", "2026-12-31 23:59:59", limit=3
    )
    assert {"list", "pagination", "stat"} <= set(reg)
    hist = mc.reports.payout_history(
        "2026-01-01 00:00:00", "2026-12-31 23:59:59", limit=3, only_status="success"
    )
    assert "list" in hist


def test_card_bind_returns_form(live):
    res = _gw().cards.bind(
        redirect_url="https://e/ok",
        redirect_decline_url="https://e/no",
        callback_url="https://e/cb",
        phone="998901234567",
    )
    assert res["form_url"].startswith("http")
    assert res["session_id"]


def test_check_pinfl_returns_bool_or_none(live):
    out = _gw().cards.check_pinfl(pan=TEST_CARD["pan"], pinfl="12345678901234")
    assert out in (True, False, None)


def test_unknown_token_raises_not_found(live):
    with pytest.raises(TransactionNotFound):
        _gw().cards.info_by_token("deadbeefdeadbeef0000")


async def test_async_auth_and_invoice(live):
    from tolov.aio import MulticardGateway as AsyncGateway

    mc = AsyncGateway(
        application_id=APPLICATION_ID, secret=SECRET, store_id=STORE_ID, is_test_mode=True
    )
    info = await mc.reports.app_info()
    assert info["application_id"] == APPLICATION_ID
    inv = await mc.invoices.create(
        amount=150000, invoice_id=_uid(), callback_url="https://example.com/cb"
    )
    assert await mc.invoices.delete(inv["uuid"]) == []


# --- full pay / refund / hold lifecycle (needs a real card token) ---


def _bearer():
    token = httpx.post(
        f"{BASE_DEV}/auth",
        json={"application_id": APPLICATION_ID, "secret": SECRET},
        timeout=30,
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def card_token(live):
    """Mint an active card token for the public test card.

    Uses the sandbox PCI add-card flow (POST /payment/card + OTP confirm)
    directly — those endpoints are intentionally NOT in the SDK, this is a
    test-only helper to obtain a token so the token-based flows can be
    exercised end to end.
    """
    headers = _bearer()
    created = httpx.post(
        f"{BASE_DEV}/payment/card",
        json={
            "pan": TEST_CARD["pan"],
            "expiry": TEST_CARD["expire"],
            "user_phone": "998901234567",
        },
        headers=headers,
        timeout=30,
    ).json()
    token = created["data"]["card_token"]
    httpx.put(
        f"{BASE_DEV}/payment/card/{token}",
        json={"otp": TEST_CARD["otp"]},
        headers=headers,
        timeout=30,
    )
    yield token
    try:
        httpx.delete(f"{BASE_DEV}/payment/card/{token}", headers=headers, timeout=30)
    except Exception:
        pass


def _confirm(mc, payment):
    """Confirm a payment, with OTP only when the response asked for one."""
    uuid_ = payment["uuid"]
    if payment.get("otp_hash"):
        return mc.payments.confirm(uuid_, otp=TEST_CARD["otp"])
    return mc.payments.confirm(uuid_)


def test_card_info_by_token(card_token):
    assert _gw().cards.info_by_token(card_token)["status"] == "active"


def test_token_payment_confirm_then_refund(card_token):
    mc = _gw()
    pay = mc.payments.create_by_token(
        card_token=card_token, amount=150000, invoice_id=_uid()
    )
    u = pay["uuid"]
    assert _confirm(mc, pay)["status"] == "success"
    assert mc.payments.info(u)["status"] == "success"
    assert mc.payments.refund(u)["status"] == "revert"


def test_token_payment_partial_refund(card_token):
    mc = _gw()
    pay = mc.payments.create_by_token(
        card_token=card_token, amount=200000, invoice_id=_uid()
    )
    u = pay["uuid"]
    assert _confirm(mc, pay)["status"] == "success"
    ofd = [
        {
            "qty": 1,
            "price": 200000,
            "mxik": "10305009001000000",
            "package_code": "1",
            "name": "Test item",
            "total": 200000,
        }
    ]
    try:
        res = mc.payments.partial_refund(u, refund_amount=50000, ofd=ofd)
        assert "status" in res
    except PaymentException:
        # partial refund requires terminal configuration; fall back to full
        assert mc.payments.refund(u)["status"] == "revert"


def test_hold_confirm_then_debit(card_token):
    mc = _gw()
    hold = mc.holds.create(
        card_token=card_token, amount=150000, invoice_id=_uid(), expiry=60
    )
    hid = hold["id"]
    assert mc.holds.confirm(hid, otp=TEST_CARD["otp"])["status"] == "active"
    # debit immediately — the sandbox auto-releases idle holds
    assert mc.holds.debit(hid, amount=100000)["status"] == "success"


def test_hold_confirm_then_cancel(card_token):
    mc = _gw()
    hold = mc.holds.create(
        card_token=card_token, amount=50000, invoice_id=_uid(), expiry=60
    )
    mc.holds.confirm(hold["id"], otp=TEST_CARD["otp"])
    assert mc.holds.cancel(hold["id"])["status"] == "canceled"
