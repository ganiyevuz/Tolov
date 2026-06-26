"""Mocked request/response tests for every Multicard sub-client method."""
import json

import respx
from httpx import Response

from conftest import AUTH_OK, BASE_DEV, STORE_ID


def _ok(data):
    return Response(200, json={"success": True, "data": data})


def _auth():
    respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))


def _body(route):
    return json.loads(route.calls.last.request.content)


def gw():
    from tolov import MulticardGateway

    return MulticardGateway(
        application_id="a", secret="s", store_id=STORE_ID, is_test_mode=True
    )


# --- invoices ---
@respx.mock
def test_invoices_create():
    _auth()
    r = respx.post(f"{BASE_DEV}/payment/invoice").mock(
        return_value=_ok({"uuid": "U", "checkout_url": "C"})
    )
    out = gw().invoices.create(
        amount=150000, invoice_id="o1", callback_url="cb", return_url="ru"
    )
    assert out == {"uuid": "U", "checkout_url": "C"}
    assert _body(r) == {
        "store_id": STORE_ID,
        "amount": 150000,
        "invoice_id": "o1",
        "callback_url": "cb",
        "ofd": [],
        "return_url": "ru",
    }


@respx.mock
def test_invoices_get_and_delete():
    _auth()
    g = respx.get(f"{BASE_DEV}/payment/invoice/U").mock(return_value=_ok({"uuid": "U"}))
    d = respx.delete(f"{BASE_DEV}/payment/invoice/U").mock(return_value=_ok([]))
    mc = gw()
    assert mc.invoices.get("U") == {"uuid": "U"}
    assert mc.invoices.delete("U") == []
    assert g.called and d.called


# --- payments ---
@respx.mock
def test_payments_create_by_token_with_split():
    _auth()
    r = respx.post(f"{BASE_DEV}/payment").mock(
        return_value=_ok({"uuid": "P", "otp_hash": None})
    )
    out = gw().payments.create_by_token(
        card_token="T",
        amount=150000,
        invoice_id="o1",
        split=[{"type": "card", "amount": 1, "details": "d"}],
    )
    assert out["uuid"] == "P"
    assert _body(r) == {
        "card": {"token": "T"},
        "amount": 150000,
        "store_id": STORE_ID,
        "invoice_id": "o1",
        "split": [{"type": "card", "amount": 1, "details": "d"}],
    }


@respx.mock
def test_payments_app_pay():
    _auth()
    r = respx.post(f"{BASE_DEV}/payment").mock(return_value=_ok({"checkout_url": "C"}))
    out = gw().payments.app_pay(payment_system="payme", amount=150000, invoice_id="o2")
    assert out == {"checkout_url": "C"}
    assert _body(r) == {
        "payment_system": "payme",
        "amount": 150000,
        "store_id": STORE_ID,
        "invoice_id": "o2",
    }


@respx.mock
def test_payments_confirm_refund_info_partial_fiscal():
    _auth()
    cf = respx.put(f"{BASE_DEV}/payment/P").mock(return_value=_ok({"status": "success"}))
    rf = respx.delete(f"{BASE_DEV}/payment/P").mock(return_value=_ok({"status": "revert"}))
    inf = respx.get(f"{BASE_DEV}/payment/P").mock(return_value=_ok({"status": "success"}))
    pr = respx.delete(f"{BASE_DEV}/payment/P/partial").mock(
        return_value=_ok({"status": "revert"})
    )
    fs = respx.patch(f"{BASE_DEV}/payment/P/fiscal").mock(return_value=_ok({}))
    mc = gw()
    mc.payments.confirm("P", otp="112233", debit_available=True)
    assert _body(cf) == {"otp": "112233", "debit_available": True}
    assert mc.payments.refund("P") == {"status": "revert"}
    assert _body(rf) == {}
    assert mc.payments.info("P") == {"status": "success"}
    mc.payments.partial_refund("P", refund_amount=20000, ofd=[{"qty": 1}])
    assert _body(pr) == {"refund_amount": 20000, "ofd": [{"qty": 1}]}
    mc.payments.send_fiscal("P", url="https://r", is_refund=True)
    assert _body(fs) == {"url": "https://r", "is_refund": True}
    assert inf.called


# --- cards ---
@respx.mock
def test_cards_methods():
    _auth()
    bind = respx.post(f"{BASE_DEV}/payment/card/bind").mock(
        return_value=_ok({"session_id": "S", "form_url": "F"})
    )
    respx.get(f"{BASE_DEV}/payment/card/bind/S").mock(
        return_value=_ok({"card_token": "T"})
    )
    respx.get(f"{BASE_DEV}/payment/card/T").mock(return_value=_ok({"card_token": "T"}))
    pinfl = respx.post(f"{BASE_DEV}/payment/card/check-pinfl").mock(
        return_value=_ok(True)
    )
    respx.delete(f"{BASE_DEV}/payment/card/T").mock(return_value=_ok([]))
    mc = gw()
    res = mc.cards.bind(
        redirect_url="o", redirect_decline_url="n", callback_url="c",
        phone="998", pinfl="123",
    )
    assert res["session_id"] == "S"
    assert _body(bind) == {
        "store_id": STORE_ID,
        "redirect_url": "o",
        "redirect_decline_url": "n",
        "callback_url": "c",
        "phone": "998",
        "pinfl": "123",
    }
    assert mc.cards.check_binding("S") == {"card_token": "T"}
    assert mc.cards.info_by_token("T") == {"card_token": "T"}
    assert mc.cards.check_pinfl(pan="8600", pinfl="123") is True
    assert _body(pinfl) == {"pan": "8600", "pinfl": "123"}
    assert mc.cards.revoke_token("T") == []


# --- holds ---
@respx.mock
def test_holds_methods():
    _auth()
    cr = respx.post(f"{BASE_DEV}/payment/hold").mock(
        return_value=_ok({"id": 7, "status": "draft"})
    )
    cf = respx.put(f"{BASE_DEV}/payment/hold/7").mock(
        return_value=_ok({"id": 7, "status": "active"})
    )
    ch = respx.put(f"{BASE_DEV}/payment/hold/7/charge").mock(
        return_value=_ok({"status": "success"})
    )
    respx.get(f"{BASE_DEV}/payment/hold/7").mock(return_value=_ok({"id": 7}))
    respx.delete(f"{BASE_DEV}/payment/hold/7").mock(
        return_value=_ok({"status": "canceled"})
    )
    mc = gw()
    assert mc.holds.create(card_token="T", amount=150000, invoice_id="o", expiry=60)["id"] == 7
    assert _body(cr) == {
        "card": {"token": "T"},
        "amount": 150000,
        "store_id": STORE_ID,
        "invoice_id": "o",
        "expiry": 60,
    }
    mc.holds.confirm(7, otp="112233")
    assert _body(cf) == {"otp": "112233"}
    mc.holds.debit(7, amount=100000)
    assert _body(ch) == {"amount": 100000}
    assert mc.holds.info(7)["id"] == 7
    assert mc.holds.cancel(7) == {"status": "canceled"}


# --- payouts ---
@respx.mock
def test_payouts_methods():
    _auth()
    cr = respx.post(f"{BASE_DEV}/payment/credit").mock(
        return_value=_ok({"uuid": "PO", "status": "success"})
    )
    cf = respx.put(f"{BASE_DEV}/payment/credit/PO").mock(
        return_value=_ok({"status": "success"})
    )
    respx.get(f"{BASE_DEV}/payment/credit/PO").mock(return_value=_ok({"uuid": "PO"}))
    mc = gw()
    mc.payouts.create(amount=10000, invoice_id="po", pan="8600", confirmable=True)
    assert _body(cr) == {
        "card": {"pan": "8600"},
        "amount": 10000,
        "store_id": STORE_ID,
        "invoice_id": "po",
        "confirmable": True,
    }
    mc.payouts.confirm("PO", otp="112233")
    assert _body(cf) == {"otp": "112233"}
    assert mc.payouts.info("PO")["uuid"] == "PO"


# --- reports ---
@respx.mock
def test_reports_methods():
    _auth()
    respx.get(f"{BASE_DEV}/payment/application").mock(return_value=_ok({"id": 4}))
    respx.get(f"{BASE_DEV}/payment/merchant-account/R").mock(
        return_value=_ok({"uuid": "R"})
    )
    reg = respx.get(f"{BASE_DEV}/payment/store/{STORE_ID}/history").mock(
        return_value=_ok({"list": []})
    )
    respx.get(f"{BASE_DEV}/payment/store/{STORE_ID}/credit-history").mock(
        return_value=_ok({"list": []})
    )
    mc = gw()
    assert mc.reports.app_info() == {"id": 4}
    assert mc.reports.recipient_details("R") == {"uuid": "R"}
    assert mc.reports.payment_registry(
        "2026-06-01 00:00:00", "2026-06-27 00:00:00", limit=5, only_status="success"
    ) == {"list": []}
    q = dict(reg.calls.last.request.url.params)
    assert q["limit"] == "5"
    assert q["only_status"] == "success"
    assert q["start_date"] == "2026-06-01 00:00:00"
    assert mc.reports.payout_history(
        "2026-06-01 00:00:00", "2026-06-27 00:00:00"
    ) == {"list": []}


# --- unified gateway interface ---
@respx.mock
def test_gateway_unified_interface():
    _auth()
    inv = respx.post(f"{BASE_DEV}/payment/invoice").mock(
        return_value=_ok({"uuid": "U", "checkout_url": "https://checkout"})
    )
    respx.get(f"{BASE_DEV}/payment/U").mock(return_value=_ok({"status": "success"}))
    respx.delete(f"{BASE_DEV}/payment/U").mock(return_value=_ok({"status": "revert"}))
    mc = gw()
    # create_payment takes SOM and converts to tiyin, returns checkout_url
    assert mc.create_payment(id="o1", amount=1500, callback_url="cb") == "https://checkout"
    assert _body(inv)["amount"] == 150000
    res = mc.check_payment("U")
    assert res["status"] == "success" and res["state"] == 2
    assert mc.cancel_payment("U") == {"status": "revert"}


# --- async parity ---
@respx.mock
async def test_async_gateway_and_subclients():
    _auth()
    respx.post(f"{BASE_DEV}/payment/invoice").mock(
        return_value=_ok({"uuid": "U", "checkout_url": "C"})
    )
    respx.get(f"{BASE_DEV}/payment/U").mock(return_value=_ok({"status": "success"}))
    respx.post(f"{BASE_DEV}/payment").mock(return_value=_ok({"uuid": "P"}))
    respx.post(f"{BASE_DEV}/payment/card/bind").mock(
        return_value=_ok({"session_id": "S", "form_url": "F"})
    )
    respx.post(f"{BASE_DEV}/payment/hold").mock(return_value=_ok({"id": 7}))
    respx.post(f"{BASE_DEV}/payment/credit").mock(return_value=_ok({"uuid": "PO"}))
    respx.get(f"{BASE_DEV}/payment/application").mock(return_value=_ok({"id": 4}))

    from tolov.aio import MulticardGateway as AsyncGateway

    mc = AsyncGateway(
        application_id="a", secret="s", store_id=STORE_ID, is_test_mode=True
    )
    assert await mc.create_payment(id="o1", amount=1500, callback_url="cb") == "C"
    assert (await mc.check_payment("U"))["state"] == 2
    assert (await mc.payments.create_by_token(card_token="T", amount=1, invoice_id="o"))["uuid"] == "P"
    assert (await mc.cards.bind(redirect_url="o", redirect_decline_url="n", callback_url="c", phone="9"))["session_id"] == "S"
    assert (await mc.holds.create(card_token="T", amount=1, invoice_id="o", expiry=60))["id"] == 7
    assert (await mc.payouts.create(amount=1, invoice_id="o", token="T"))["uuid"] == "PO"
    assert (await mc.reports.app_info())["id"] == 4
