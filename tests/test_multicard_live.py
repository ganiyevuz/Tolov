"""Live integration tests against the Multicard sandbox (dev-mesh).

Uses the public sandbox credentials from conftest. Run only these with:
    pytest -m live
Skip them with:
    pytest -m 'not live'
They auto-skip when the sandbox is unreachable (see the `live` fixture).
"""
import uuid

import pytest

from conftest import APPLICATION_ID, SECRET, STORE_ID, TEST_CARD
from tolov import MulticardGateway
from tolov.core.exceptions import TransactionNotFound

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
