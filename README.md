<h1 align="center">
  Tolov
</h1>

<h3 align="center">
<strong>Unified payment SDK for Uzbekistan</strong></h3>

<p align="center">
  <a href="https://badge.fury.io/py/tolov"><img src="https://badge.fury.io/py/tolov@2x.png?icon=si%3Apython" alt="PyPI version" height="18"></a>
  <a href="https://pypi.org/project/tolov/"><img src="https://img.shields.io/pypi/pyversions/tolov.svg" alt="Python"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://pypi.org/project/tolov"><img src="https://img.shields.io/pypi/dm/tolov.svg?color=blue" alt="Downloads"></a>
</p>

<p align="center">
  <strong>Accept payments from every major provider in Uzbekistan with a single, beautiful API.</strong><br>
  <sub>Payme &bull; Click &bull; Uzum &bull; Paynet &bull; Octo &bull; Multicard &mdash; sync & async &mdash; Django & FastAPI ready</sub>
</p>

<br>

<p align="center"><strong>One <code>MulticardGateway</code> integration &rarr; accept 18+ payment methods on a single checkout</strong></p>

<div align="center">
<table>
<tr>
<td align="center" width="80"><img src="assets/providers/payme.svg" width="46" height="46" alt="Payme"><br><sub>Payme</sub></td>
<td align="center" width="80"><img src="assets/providers/click.svg" width="46" height="46" alt="Click"><br><sub>Click</sub></td>
<td align="center" width="80"><img src="assets/providers/uzum.svg" width="46" height="46" alt="Uzum"><br><sub>Uzum</sub></td>
<td align="center" width="80"><img src="assets/providers/alif.svg" width="46" height="46" alt="Alif"><br><sub>Alif</sub></td>
<td align="center" width="80"><img src="assets/providers/apexbank.svg" width="46" height="46" alt="Apex"><br><sub>Apex</sub></td>
<td align="center" width="80"><img src="assets/providers/davrbank.svg" width="46" height="46" alt="Davr"><br><sub>Davr</sub></td>
<td align="center" width="80"><img src="assets/providers/asiaalliancebank.svg" width="46" height="46" alt="Alliance"><br><sub>Alliance</sub></td>
<td align="center" width="80"><img src="assets/providers/rahmat.svg" width="46" height="46" alt="Rahmat"><br><sub>Rahmat</sub></td>
<td align="center" width="80"><img src="assets/providers/asterium.svg" width="46" height="46" alt="Asterium"><br><sub>Asterium</sub></td>
</tr>
<tr>
<td align="center" width="80"><img src="assets/providers/paynet.svg" width="46" height="46" alt="Paynet"><br><sub>Paynet</sub></td>
<td align="center" width="80"><img src="assets/providers/anorbank.svg" width="46" height="46" alt="Anor"><br><sub>Anor</sub></td>
<td align="center" width="80"><img src="assets/providers/xazna.svg" width="46" height="46" alt="Xazna"><br><sub>Xazna</sub></td>
<td align="center" width="80"><img src="assets/providers/beepul.svg" width="46" height="46" alt="Beepul"><br><sub>Beepul</sub></td>
<td align="center" width="80"><img src="assets/providers/oson.svg" width="46" height="46" alt="Oson"><br><sub>Oson</sub></td>
<td align="center" width="80"><img src="assets/providers/trastpay.svg" width="46" height="46" alt="Trast"><br><sub>Trast</sub></td>
<td align="center" width="80"><img src="assets/providers/ofb.svg" width="46" height="46" alt="OFB"><br><sub>OFB</sub></td>
<td align="center" width="80"><img src="assets/providers/morpara.svg" width="46" height="46" alt="Morpara"><br><sub>Morpara</sub></td>
<td align="center" width="80"><img src="assets/providers/sbp.svg" width="46" height="46" alt="SBP"><br><sub>&#1057;&#1041;&#1055;</sub></td>
</tr>
</table>
</div>

---

<table>
<tr>
<td width="50%">

**Supported Providers**

| Provider | Pay Link | API | Webhooks |
|----------|:--------:|:---:|:--------:|
| Payme    | +        | +   | +        |
| Click    | +        | +   | +        |
| Uzum     | +        | +   | +        |
| Paynet   | +        | -   | +        |
| Octo     | +        | +   | +        |
| Multicard | +       | +   | +        |

</td>
<td width="50%">

**Key Features**

- Sync & async (httpx)
- Django, FastAPI integrations
- Webhook handlers out of the box
- Automatic transaction tracking
- Card tokenization (Payme, Click)
- Receipt management (Payme)
- Refund API (Octo, Uzum, Click)

</td>
</tr>
</table>

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Payment Links](#payment-links)
  - [Async Usage](#async-usage)
  - [Receipts & Cards (Payme)](#receipts--cards-payme)
  - [Card Tokens (Click)](#card-tokens-click)
  - [Octo Payments](#octo-payments)
  - [Multicard](#multicard)
- [Django Integration](#django-integration)
- [FastAPI Integration](#fastapi-integration)
- [API Reference](#api-reference)
- [Development](#development)
- [License](#license)

---

## Installation

```bash
pip install tolov
```

With framework extras:

```bash
pip install tolov[django]     # Django + DRF
pip install tolov[fastapi]    # FastAPI + SQLAlchemy
```

---

## Quick Start

### Payment Links

```python
from tolov import PaymeGateway, ClickGateway, UzumGateway, OctoGateway
from tolov.gateways.paynet.client import PaynetGateway

# --- Payme ---
payme = PaymeGateway(payme_id="ID", payme_key="KEY", is_test_mode=True)

payme_url = payme.create_payment(
    id="order_1",
    amount=150_000,                  # in som
    return_url="https://example.com/done",
    account_field_name="order_id",   # Payme-specific (default: "order_id")
)

# --- Click ---
click = ClickGateway(
    service_id="SID", merchant_id="MID",
    merchant_user_id="MUID", secret_key="SECRET",
)

click_url = click.create_payment(
    id="order_1",
    amount=150_000,
    return_url="https://example.com/done",
)

# --- Uzum ---
uzum = UzumGateway(service_id="498624684")

uzum_url = uzum.create_payment(
    id="order_1",
    amount=100_000,                  # in som, converted to tiyin automatically
    return_url="https://example.com/done",
)

# --- Octo ---
octo = OctoGateway(
    octo_shop_id=123,
    octo_secret="your-secret",
    notify_url="https://example.com/octo/webhook",
)

octo_url = octo.create_payment(
    id="order_1",
    amount=50_000,
    return_url="https://example.com/done",
)

# --- Paynet ---
paynet = PaynetGateway(merchant_id=12345)

paynet_url = paynet.create_payment(
    id="order_1",
    amount=15_000_000,               # in tiyin
)
# Without amount (configured on Paynet side):
paynet_url = paynet.create_payment(id="order_1")
```

### Async Usage

Same class names, same methods — just import from `tolov.aio`:

```python
from tolov.aio import PaymeGateway, ClickGateway, OctoGateway, UzumGateway

payme = PaymeGateway(payme_id="ID", payme_key="KEY")

# Sync methods (no HTTP) work as-is
url = payme.create_payment(id="order_1", amount=150_000, return_url="...")

# Async methods (HTTP calls) use await
status = await payme.check_payment(transaction_id="receipt_abc")
result = await payme.cancel_payment(transaction_id="receipt_abc")

# Octo — fully async
octo = OctoGateway(octo_shop_id=123, octo_secret="secret", notify_url="...")
url = await octo.create_payment(id="order_1", amount=50_000, return_url="...")
status = await octo.check_payment(transaction_id="shop_tx_123")
refund = await octo.cancel_payment(transaction_id="octo-uuid", amount=50_000)
```

### Receipts & Cards (Payme)

```python
from tolov import PaymeGateway

payme = PaymeGateway(payme_id="ID", payme_key="KEY")

# Cards
card = payme.cards.create(card_number="8600...", expire_date="03/25")
payme.cards.get_verify_code(token=card["result"]["card"]["token"])
payme.cards.verify(token=card["result"]["card"]["token"], code="123456")
payme.cards.check(token="...")
payme.cards.remove(token="...")

# Receipts
receipt = payme.receipts.create(
    amount=500_000,                       # in tiyin
    account={"order_id": "123"},
    description="Payment for order #123",
)
payme.receipts.pay(receipt_id="...", token="card_token")
payme.receipts.check(receipt_id="...")
payme.receipts.cancel(receipt_id="...", reason="Customer request")
payme.receipts.send(receipt_id="...", phone="998901234567")
```

Async variants — same interface:

```python
from tolov.aio import PaymeGateway

payme = PaymeGateway(payme_id="ID", payme_key="KEY")

card = await payme.cards.create(card_number="8600...", expire_date="03/25")
receipt = await payme.receipts.create(amount=500_000, account={"order_id": "123"})
```

### Card Tokens (Click)

```python
from tolov import ClickGateway

click = ClickGateway(
    service_id="SID", merchant_id="MID",
    merchant_user_id="MUID", secret_key="SECRET",
)

# Request card token
result = click.card_token_request(
    card_number="5614681005030279",
    expire_date="0330",
)

# Verify with SMS code
click.card_token_verify(card_token="token_abc", sms_code="12345")

# Pay using token
click.card_token_payment(
    card_token="token_abc",
    amount=100_000,
    transaction_parameter="unique_tx_id",
)
```

### Octo Payments

```python
from tolov import OctoGateway

octo = OctoGateway(
    octo_shop_id=123,
    octo_secret="your-secret",
    notify_url="https://example.com/octo/webhook",
    is_test_mode=True,
)

# Create payment (one-stage, auto-capture)
url = octo.create_payment(
    id="order_1",
    amount=50_000,
    return_url="https://example.com/done",
    currency="UZS",
    language="uz",
    ttl=15,                             # payment page TTL in minutes
)
# Redirect user to url

# Check status
status = octo.check_payment(transaction_id="order_1")

# Refund
refund = octo.cancel_payment(
    transaction_id="octo-payment-uuid",  # octo_payment_UUID from create response
    amount=50_000,
)
```

### Multicard

Multicard uses token-based auth (the SDK fetches and refreshes the JWT for you)
and a single `store_id`. The top-level `create_payment` opens an invoice
(payment page) and returns its `checkout_url`.

> **Multicard is an aggregator** — one `MulticardGateway` integration accepts
> every method shown at the top of this README (cards, wallets, and banks) on a
> single checkout page, with no separate per-provider setup.

```python
from tolov import MulticardGateway

mc = MulticardGateway(
    application_id="your_application_id",
    secret="your_secret",
    store_id=123,
    is_test_mode=True,
)

# Create an invoice — returns checkout_url (amount in som)
url = mc.create_payment(
    id="order_1",
    amount=150_000,
    return_url="https://example.com/done",
    callback_url="https://example.com/payments/webhook/multicard",
)

# Check status (by Multicard transaction uuid)
status = mc.check_payment(transaction_id="<uuid>")   # -> {"status", "state", "data"}

# Refund
mc.cancel_payment(transaction_id="<uuid>")

# Lower-level sub-clients (amounts in tiyin):
mc.invoices.create(amount=15_000_000, invoice_id="order_1", callback_url="...")
mc.invoices.get("<uuid>")
mc.invoices.delete("<uuid>")     # annul an unpaid invoice
mc.payments.info("<uuid>")
mc.payments.refund("<uuid>")
```

Async — same names, `await` the HTTP calls:

```python
from tolov.aio import MulticardGateway

mc = MulticardGateway(application_id="...", secret="...", store_id=123)
url = await mc.create_payment(id="order_1", amount=150_000, callback_url="...")
status = await mc.check_payment(transaction_id="<uuid>")
```

**Card binding (form).** Redirect the user to `form_url`; once they finish,
read the resulting `card_token` either from the (unsigned) bind callback or by
polling `check_binding(session_id)`. Store the token yourself — tolov does not
persist cards.

```python
res = mc.cards.bind(
    redirect_url="https://example.com/cards/ok",
    redirect_decline_url="https://example.com/cards/fail",
    callback_url="https://example.com/cards/callback",
    phone="998901234567",
)
session_id, form_url = res["session_id"], res["form_url"]   # redirect user to form_url

binding = mc.cards.check_binding(session_id)   # -> card_token, card_pan, status, ...
mc.cards.info_by_token("<card_token>")
mc.cards.check_pinfl(pan="8600...", pinfl="12345678901234")   # Uzcard/Humo only
mc.cards.revoke_token("<card_token>")
```

**Token payments, refunds & fiscal** (amounts in tiyin):

```python
# Charge a saved card token (optional split + OFD fiscal data)
payment = mc.payments.create_by_token(
    card_token="<card_token>",
    amount=500_000,
    invoice_id="order_1",
    split=[{"type": "card", "amount": 100_000, "details": "partner share",
            "recipient": "<bank-details-uuid>"}],
)
# If payment["otp_hash"] is not null, an SMS code is required:
mc.payments.confirm(payment["uuid"], otp="123456")

# Pay via an external app (payme/click/uzum/...) — returns checkout_url/deeplink
app = mc.payments.app_pay(payment_system="payme", amount=500_000, invoice_id="order_2")

mc.payments.info("<uuid>")
mc.payments.refund("<uuid>")                                  # full refund
mc.payments.partial_refund("<uuid>", refund_amount=20_000, ofd=[...])
mc.payments.send_fiscal("<uuid>", url="https://ofd.example/check/...")
```

**Holds** (block funds, then debit or cancel; `expiry` in minutes, ≤ 30 days):

```python
hold = mc.holds.create(card_token="<card_token>", amount=500_000,
                       invoice_id="order_1", expiry=60)
hold_id = hold["id"]
mc.holds.confirm(hold_id, otp="123456")     # block the funds
mc.holds.debit(hold_id, amount=300_000)     # capture (partial allowed)
# or release before capture:
mc.holds.cancel(hold_id)
mc.holds.info(hold_id)
```

**Payouts** (credit a card by `pan` or saved `token`; `kyc_data` required > 10M som):

```python
payout = mc.payouts.create(amount=10_000, invoice_id="po_1", token="<card_token>")
# If created with confirmable=True, confirm with an OTP:
mc.payouts.confirm(payout["uuid"], otp="123456")
mc.payouts.info("<uuid>")
```

**Reporting** (read-only; dates `YYYY-mm-dd HH:MM:SS`, GMT+5):

```python
mc.reports.app_info()                       # wallet balance, OTP settings, ...
mc.reports.recipient_details("<merchant-account-uuid>")
mc.reports.payment_registry("2026-06-01 00:00:00", "2026-06-26 23:59:59", limit=100)
mc.reports.payout_history("2026-06-01 00:00:00", "2026-06-26 23:59:59")
```

---

## Django Integration

### 1. Settings

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "tolov.integrations.django",
]

TOLOV = {
    "PAYME": {
        "PAYME_ID": "your_payme_id",
        "PAYME_KEY": "your_payme_key",
        "ACCOUNT_MODEL": "orders.models.Order",
        "ACCOUNT_FIELD": "id",
        "AMOUNT_FIELD": "amount",
        "ONE_TIME_PAYMENT": True,
    },
    "CLICK": {
        "SERVICE_ID": "your_service_id",
        "MERCHANT_ID": "your_merchant_id",
        "MERCHANT_USER_ID": "your_merchant_user_id",
        "SECRET_KEY": "your_secret_key",
        "ACCOUNT_MODEL": "orders.models.Order",
        "ACCOUNT_FIELD": "id",
        "COMMISSION_PERCENT": 0.0,
        "ONE_TIME_PAYMENT": True,
    },
    "UZUM": {
        "SERVICE_ID": "your_service_id",
        "USERNAME": "your_username",
        "PASSWORD": "your_password",
        "ACCOUNT_MODEL": "orders.models.Order",
        "ACCOUNT_FIELD": "order_id",
        "AMOUNT_FIELD": "amount",
        "ONE_TIME_PAYMENT": True,
    },
    "PAYNET": {
        "SERVICE_ID": "your_service_id",
        "USERNAME": "your_username",
        "PASSWORD": "your_password",
        "ACCOUNT_MODEL": "orders.models.Order",
        "ACCOUNT_FIELD": "id",
        "AMOUNT_FIELD": "amount",
        "ONE_TIME_PAYMENT": True,
    },
    "MULTICARD": {
        "APPLICATION_ID": "your_application_id",
        "SECRET": "your_secret",          # also signs the success callback
        "STORE_ID": 123,
        # "CALLBACK_SECRET": "...",       # optional; defaults to SECRET
        "ACCOUNT_MODEL": "orders.models.Order",
        "ACCOUNT_FIELD": "id",
    },
}
```

> **Note:** `IS_TEST_MODE` is set when creating gateway instances (`PaymeGateway(is_test_mode=True)`), not in webhook settings. Webhooks use the same URL in both environments.

### 2. Order Model

```python
# models.py
from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    product_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
```

### 3. Webhook Handlers

```python
# views.py
from tolov.integrations.django.views import (
    BasePaymeWebhookView,
    BaseClickWebhookView,
    BaseUzumWebhookView,
    BasePaynetWebhookView,
    BaseOctoWebhookView,
    BaseMulticardWebhookView,
)
from .models import Order


class PaymeWebhookView(BasePaymeWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "paid"
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "cancelled"
        order.save()

    def get_check_data(self, params, account):  # optional
        return {
            "detail": {
                "receipt_type": 0,
                "items": [{
                    "title": account.product_name,
                    "price": int(account.amount * 100),
                    "count": 1,
                    "code": "00001",
                    "units": 1,
                    "vat_percent": 0,
                    "package_code": "123456",
                }],
            }
        }


class ClickWebhookView(BaseClickWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "paid"
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "cancelled"
        order.save()


class UzumWebhookView(BaseUzumWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "paid"
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "cancelled"
        order.save()

    def get_check_data(self, params, account):  # optional
        return {"fio": {"value": "Ivanov Ivan"}}


class PaynetWebhookView(BasePaynetWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "paid"
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "cancelled"
        order.save()

    def get_check_data(self, params, account):  # optional
        return {
            "fields": {
                "first_name": account.user.first_name,
                "balance": str(account.amount),
            }
        }


class OctoWebhookView(BaseOctoWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "paid"
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "cancelled"
        order.save()


class MulticardWebhookView(BaseMulticardWebhookView):
    # Multicard's success callback fires only on a successful payment;
    # the signature is verified for you before this runs.
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = "paid"
        order.save()
```

### 4. URLs

```python
# urls.py
from django.urls import path
from .views import (
    PaymeWebhookView, ClickWebhookView, UzumWebhookView,
    PaynetWebhookView, OctoWebhookView,
)

urlpatterns = [
    path("payments/webhook/payme/", PaymeWebhookView.as_view()),
    path("payments/webhook/click/", ClickWebhookView.as_view()),
    path("payments/webhook/uzum/<str:action>/", UzumWebhookView.as_view()),
    path("payments/webhook/paynet/", PaynetWebhookView.as_view()),
    path("payments/webhook/octo/", OctoWebhookView.as_view()),
    path("payments/webhook/multicard/", MulticardWebhookView.as_view()),
]
```

---

## FastAPI Integration

### 1. Database Setup

```python
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

from tolov.integrations.fastapi.models import run_migrations

engine = create_engine("sqlite:///./payments.db")
Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    amount = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Create payment transaction tables
run_migrations(engine)

# Create your tables
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### 2. Webhook Handlers

```python
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from tolov.integrations.fastapi import (
    PaymeWebhookHandler,
    ClickWebhookHandler,
    MulticardWebhookHandler,
)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CustomPaymeWebhookHandler(PaymeWebhookHandler):
    def successfully_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()

    def cancelled_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "cancelled"
        self.db.commit()


class CustomClickWebhookHandler(ClickWebhookHandler):
    def successfully_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()

    def cancelled_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "cancelled"
        self.db.commit()


@app.post("/payments/payme/webhook")
async def payme_webhook(request: Request, db: Session = Depends(get_db)):
    handler = CustomPaymeWebhookHandler(
        db=db,
        payme_id="your_payme_id",
        payme_key="your_payme_key",
        account_model=Order,
        account_field="id",
        amount_field="amount",
    )
    return await handler.handle_webhook(request)


@app.post("/payments/click/webhook")
async def click_webhook(request: Request, db: Session = Depends(get_db)):
    handler = CustomClickWebhookHandler(
        db=db,
        service_id="your_service_id",
        secret_key="your_secret_key",
        account_model=Order,
        account_field="id",
        one_time_payment=True,
    )
    return await handler.handle_webhook(request)


class CustomMulticardWebhookHandler(MulticardWebhookHandler):
    def successfully_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()


@app.post("/payments/multicard/webhook")
async def multicard_webhook(request: Request, db: Session = Depends(get_db)):
    handler = CustomMulticardWebhookHandler(
        db=db,
        secret="your_secret",          # the secret that signs the callback
        account_model=Order,
        account_field="id",
    )
    return await handler.handle_webhook(request)
```

---

## API Reference

### Gateway Constructors

| Gateway | Required Parameters |
|---------|-------------------|
| `PaymeGateway` | `payme_id`, `payme_key` |
| `ClickGateway` | `service_id`, `merchant_id` |
| `UzumGateway` | `service_id` |
| `PaynetGateway` | `merchant_id` |
| `OctoGateway` | `octo_shop_id`, `octo_secret` |
| `MulticardGateway` | `application_id`, `secret`, `store_id` |

All gateways accept `is_test_mode=True` for sandbox environments.

### Unified Interface

Every gateway implements `create_payment()`, `check_payment()`, and `cancel_payment()`:

```
create_payment(id, amount, ...) -> str           # Payment URL
check_payment(transaction_id)   -> dict          # Status + details
cancel_payment(transaction_id)  -> dict          # Cancellation result
```

### Sync vs Async

```python
# Sync
from tolov import PaymeGateway, ClickGateway, OctoGateway, UzumGateway, MulticardGateway

# Async (same class names, same methods)
from tolov.aio import PaymeGateway, ClickGateway, OctoGateway, UzumGateway, MulticardGateway
```

Methods that make HTTP calls become `async` automatically. Methods that only build URLs (like `create_payment` for Payme, Click, Uzum, Paynet) remain synchronous even on async gateways.

---

## Development

```bash
uv sync                          # install the dev environment
uv run pytest                    # full suite (live tests skip if the sandbox is unreachable)
uv run pytest -m "not live"      # offline only (respx-mocked)
uv run pytest -m live            # live Multicard sandbox integration tests
```

Release notes live in [CHANGELOG.md](CHANGELOG.md).

---

## License

[MIT](LICENSE.txt)
