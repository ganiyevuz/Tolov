"""Django Multicard success-callback webhook tests."""
import json
from hashlib import md5

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

SECRET = "testsecret"


def cb(store_id=105, invoice="inv-1", amount=500000, uuid="u-1", secret=SECRET, **extra):
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
    body.update(extra)
    body["sign"] = md5(f"{store_id}{invoice}{amount}{secret}".encode()).hexdigest()
    return body


@pytest.fixture
def set_tolov():
    old = getattr(settings, "TOLOV", None)
    yield lambda cfg: setattr(settings, "TOLOV", {"MULTICARD": cfg})
    settings.TOLOV = old


def _post(body):
    from tolov.integrations.django.webhooks import MulticardWebhook

    request = RequestFactory().post(
        "/wh", data=json.dumps(body), content_type="application/json"
    )
    return MulticardWebhook().post(request)


@pytest.mark.usefixtures("django_migrated")
class TestDjangoMulticardWebhook:
    def test_valid_signature_marks_paid(self, set_tolov):
        set_tolov({"SECRET": SECRET})
        from tolov.integrations.django.models import PaymentTransaction

        assert _post(cb(uuid="dj-ok")).status_code == 200
        tx = PaymentTransaction.objects.get(
            gateway="multicard", transaction_id="dj-ok"
        )
        assert tx.state == PaymentTransaction.SUCCESSFULLY
        assert str(tx.amount) == "5000.00"  # 500000 tiyin -> som
        assert tx.account_id == "inv-1"
        assert tx.extra_data["card_token"] == "TKN"
        assert tx.performed_at is not None

    def test_bad_signature_rejected(self, set_tolov):
        set_tolov({"SECRET": SECRET})
        body = cb(uuid="dj-bad")
        body["sign"] = "deadbeef"
        assert _post(body).status_code == 403

    def test_missing_secret_fails_closed(self, set_tolov):
        set_tolov({})
        with pytest.raises(ImproperlyConfigured):
            _post(cb(uuid="dj-x"))

    def test_store_mismatch_rejected(self, set_tolov):
        set_tolov({"SECRET": SECRET, "STORE_ID": 999})
        assert _post(cb(store_id=105, uuid="dj-store")).status_code == 403

    def test_matching_store_accepted(self, set_tolov):
        set_tolov({"SECRET": SECRET, "STORE_ID": 105})
        assert _post(cb(store_id=105, uuid="dj-store-ok")).status_code == 200

    def test_idempotent(self, set_tolov):
        set_tolov({"SECRET": SECRET})
        from tolov.integrations.django.models import PaymentTransaction

        _post(cb(uuid="dj-idem"))
        _post(cb(uuid="dj-idem"))
        assert (
            PaymentTransaction.objects.filter(transaction_id="dj-idem").count() == 1
        )
