"""Multicard internal webhook handler (success callback).

Verifies the success-callback signature md5(store_id+invoice_id+amount+secret)
and upserts a PaymentTransaction. The official docs claim sha1(uuid+...); that is
WRONG for this callback — see the multicard-callback-sign-formula note.
"""
import hmac
import json
from decimal import Decimal
from hashlib import md5

from loguru import logger

from django.views import View
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.module_loading import import_string

from tolov.core.base import BasePaymentProcessor
from tolov.integrations.django.models import PaymentTransaction


class MulticardWebhook(BasePaymentProcessor, View):
    """Base Multicard success-callback handler for Django."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cfg = settings.TOLOV.get("MULTICARD", {})
        self.secret = cfg.get("CALLBACK_SECRET") or cfg.get("SECRET", "")
        self.account_field = cfg.get("ACCOUNT_FIELD", "id")
        model_path = cfg.get("ACCOUNT_MODEL")
        try:
            self.account_model = import_string(model_path) if model_path else None
        except ImportError:
            logger.error("Could not import TOLOV.MULTICARD.ACCOUNT_MODEL={}", model_path)
            raise

    def _expected_sign(self, params):
        raw = (
            f"{params.get('store_id')}{params.get('invoice_id')}"
            f"{params.get('amount')}{self.secret}"
        )
        return md5(raw.encode("utf-8")).hexdigest()

    def post(self, request, *args, **kwargs):
        try:
            params = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "invalid json"}, status=400)

        received = params.get("sign", "")
        if not hmac.compare_digest(received, self._expected_sign(params)):
            logger.warning(
                "Multicard webhook: bad signature for invoice {}",
                params.get("invoice_id"),
            )
            return HttpResponseForbidden("invalid sign")

        transaction = self._upsert(params)
        self.successfully_payment(params, transaction)
        return JsonResponse({"success": True})

    def _upsert(self, params):
        account_id = params.get("invoice_id")
        if self.account_model is not None:
            account = self._find_account(account_id)
            if account is not None:
                account_id = account.id

        transaction = PaymentTransaction.create_transaction(
            gateway=PaymentTransaction.MULTICARD,
            transaction_id=params.get("uuid"),
            account_id=account_id,
            amount=Decimal(str(params.get("amount", 0))) / 100,
            extra_data={
                "card_token": params.get("card_token"),
                "card_pan": params.get("card_pan"),
                "ps": params.get("ps"),
                "receipt_url": params.get("receipt_url"),
                "phone": params.get("phone"),
                "billing_id": params.get("billing_id"),
                "payment_time": params.get("payment_time"),
                "raw_params": params,
            },
        )
        transaction.mark_as_paid()
        return transaction

    def _find_account(self, value):
        lookup = "id" if self.account_field == "order_id" else self.account_field
        if lookup == "id" and isinstance(value, str) and value.isdigit():
            value = int(value)
        try:
            return self.account_model._default_manager.get(**{lookup: value})
        except self.account_model.DoesNotExist:
            logger.warning("Multicard webhook: account {}={} not found", lookup, value)
            return None

    def successfully_payment(self, params, transaction):
        """Override to react to a successful payment."""
