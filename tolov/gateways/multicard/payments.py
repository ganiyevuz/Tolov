"""Multicard payments sub-client.

Token payments (with optional split), app payments (payme/click/uzum/...),
OTP confirmation, refunds (full + partial), fiscal links, and payment lookup.
``amount`` / ``refund_amount`` are in tiyin.
"""
from typing import Any, Dict, List, Optional

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardPayments:
    """Partner-page payments by card token + lifecycle operations."""

    def __init__(self, session, store_id=None):
        self.session = session
        self.store_id = store_id

    # --- request builders (shared by sync + async) ---
    def _build_create_by_token(
        self,
        card_token,
        amount,
        invoice_id,
        *,
        callback_url=None,
        device_details=None,
        ofd=None,
        split=None,
        billing_id=None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "card": {"token": card_token},
            "amount": int(amount),
            "store_id": self.store_id,
            "invoice_id": str(invoice_id),
        }
        for key, val in (
            ("callback_url", callback_url),
            ("device_details", device_details),
            ("ofd", ofd),
            ("split", split),
            ("billing_id", billing_id),
        ):
            if val is not None:
                body[key] = val
        return body

    def _build_app_pay(
        self,
        payment_system,
        amount,
        invoice_id,
        *,
        callback_url=None,
        ofd=None,
        billing_id=None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "payment_system": payment_system,
            "amount": int(amount),
            "store_id": self.store_id,
            "invoice_id": str(invoice_id),
        }
        for key, val in (
            ("callback_url", callback_url),
            ("ofd", ofd),
            ("billing_id", billing_id),
        ):
            if val is not None:
                body[key] = val
        return body

    def _build_confirm(self, otp=None, debit_available=None) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if otp is not None:
            body["otp"] = otp
        if debit_available is not None:
            body["debit_available"] = debit_available
        return body

    def _build_partial_refund(self, refund_amount, ofd, card_pan=None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"refund_amount": int(refund_amount), "ofd": ofd}
        if card_pan is not None:
            body["card_pan"] = card_pan
        return body

    def _build_fiscal(self, url, is_refund=None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"url": url}
        if is_refund is not None:
            body["is_refund"] = is_refund
        return body

    # --- operations ---
    @handle_exceptions
    def info(self, uuid) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.PAYMENT}/{uuid}")

    @handle_exceptions
    def create_by_token(self, card_token, amount, invoice_id, **kwargs) -> Dict[str, Any]:
        """Charge a saved card token. Pass ``split=[...]`` for a split payment."""
        body = self._build_create_by_token(card_token, amount, invoice_id, **kwargs)
        return self.session.post(MulticardEndpoints.PAYMENT, json_data=body)

    @handle_exceptions
    def app_pay(self, payment_system, amount, invoice_id, **kwargs) -> Dict[str, Any]:
        """Create a payment via an app (payme/click/uzum/...). Returns checkout_url."""
        body = self._build_app_pay(payment_system, amount, invoice_id, **kwargs)
        return self.session.post(MulticardEndpoints.PAYMENT, json_data=body)

    @handle_exceptions
    def confirm(self, uuid, otp=None, *, debit_available=None) -> Dict[str, Any]:
        """Confirm a payment (empty body when otp_hash was null / no SMS)."""
        body = self._build_confirm(otp, debit_available)
        return self.session.put(f"{MulticardEndpoints.PAYMENT}/{uuid}", json_data=body)

    @handle_exceptions
    def refund(self, uuid) -> Dict[str, Any]:
        return self.session.delete(
            f"{MulticardEndpoints.PAYMENT}/{uuid}", json_data={}
        )

    @handle_exceptions
    def partial_refund(
        self, uuid, refund_amount, ofd: List[Dict[str, Any]], *, card_pan=None
    ) -> Dict[str, Any]:
        body = self._build_partial_refund(refund_amount, ofd, card_pan)
        return self.session.delete(
            f"{MulticardEndpoints.PAYMENT}/{uuid}/partial", json_data=body
        )

    @handle_exceptions
    def send_fiscal(self, uuid, url, *, is_refund: Optional[bool] = None) -> Dict[str, Any]:
        body = self._build_fiscal(url, is_refund)
        return self.session.patch(
            f"{MulticardEndpoints.PAYMENT}/{uuid}/fiscal", json_data=body
        )
