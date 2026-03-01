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
  <sub>Payme &bull; Click &bull; Uzum &bull; Paynet &bull; Octo &mdash; sync & async &mdash; Django & FastAPI ready</sub>
</p>

<br>

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

</td>
<td width="50%">

**Key Features**

- Sync & async (httpx)
- Django, FastAPI, Flask integrations
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
- [Django Integration](#django-integration)
- [FastAPI Integration](#fastapi-integration)
- [API Reference](#api-reference)
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
pip install tolov[flask]      # Flask + Flask-SQLAlchemy
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
from tolov.integrations.fastapi import PaymeWebhookHandler, ClickWebhookHandler

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
from tolov import PaymeGateway, ClickGateway, OctoGateway, UzumGateway

# Async (same class names, same methods)
from tolov.aio import PaymeGateway, ClickGateway, OctoGateway, UzumGateway
```

Methods that make HTTP calls become `async` automatically. Methods that only build URLs (like `create_payment` for Payme, Click, Uzum, Paynet) remain synchronous even on async gateways.

---

## License

[MIT](LICENSE.txt)
