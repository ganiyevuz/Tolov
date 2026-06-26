"""Multicard payouts sub-client (credit funds to a card).

Send money to a card by ``pan`` or saved ``token``. With ``confirmable=True``
the payout needs an OTP confirm step; otherwise it completes in one request.
``kyc_data`` is required for amounts over 10M som. Amounts are in tiyin.
"""
from typing import Any, Dict, Optional

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardPayouts:
    """Card payouts addressed by the payout ``uuid``."""

    def __init__(self, session, store_id):
        self.session = session
        self.store_id = store_id

    def _build_create(
        self,
        amount,
        invoice_id,
        *,
        pan=None,
        token=None,
        confirmable=None,
        device_details=None,
        kyc_data=None,
    ) -> Dict[str, Any]:
        card: Dict[str, Any] = {}
        if pan is not None:
            card["pan"] = pan
        if token is not None:
            card["token"] = token
        body: Dict[str, Any] = {
            "card": card,
            "amount": int(amount),
            "store_id": self.store_id,
            "invoice_id": str(invoice_id),
        }
        for key, val in (
            ("confirmable", confirmable),
            ("device_details", device_details),
            ("kyc_data", kyc_data),
        ):
            if val is not None:
                body[key] = val
        return body

    @handle_exceptions
    def create(
        self, amount, invoice_id, *, pan: Optional[str] = None,
        token: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Create a payout. Provide exactly one of ``pan`` or ``token``."""
        body = self._build_create(amount, invoice_id, pan=pan, token=token, **kwargs)
        return self.session.post(MulticardEndpoints.CREDIT, json_data=body)

    @handle_exceptions
    def confirm(self, uuid, otp) -> Dict[str, Any]:
        return self.session.put(
            f"{MulticardEndpoints.CREDIT}/{uuid}", json_data={"otp": otp}
        )

    @handle_exceptions
    def info(self, uuid) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.CREDIT}/{uuid}")
