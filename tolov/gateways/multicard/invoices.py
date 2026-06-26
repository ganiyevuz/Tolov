"""Multicard invoice (payment-page) sub-client."""
from typing import Any, Dict

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardInvoices:
    """Create / read / annul invoices. ``amount`` is in tiyin."""

    def __init__(self, session, store_id):
        self.session = session
        self.store_id = store_id

    def _build_create(
        self,
        amount,
        invoice_id,
        callback_url,
        *,
        ofd=None,
        return_url=None,
        return_error_url=None,
        lang=None,
        sms=None,
        ttl=None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "store_id": self.store_id,
            "amount": int(amount),
            "invoice_id": str(invoice_id),
            "callback_url": callback_url,
            "ofd": ofd if ofd is not None else [],
        }
        for key, val in (
            ("return_url", return_url),
            ("return_error_url", return_error_url),
            ("lang", lang),
            ("sms", sms),
            ("ttl", ttl),
        ):
            if val is not None:
                body[key] = val
        return body

    @handle_exceptions
    def create(self, amount, invoice_id, callback_url, **kwargs) -> Dict[str, Any]:
        body = self._build_create(amount, invoice_id, callback_url, **kwargs)
        return self.session.post(MulticardEndpoints.INVOICE, json_data=body)

    @handle_exceptions
    def get(self, uuid) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.INVOICE}/{uuid}")

    @handle_exceptions
    def delete(self, uuid) -> Dict[str, Any]:
        return self.session.delete(f"{MulticardEndpoints.INVOICE}/{uuid}")
