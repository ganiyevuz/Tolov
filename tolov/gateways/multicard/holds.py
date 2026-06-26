"""Multicard holds sub-client (block funds, then debit or cancel).

Flow: create -> confirm (block) -> debit (full or partial) or cancel.
Amounts are in tiyin; ``expiry`` is the hold lifetime in minutes (1..43200).
"""
from typing import Any, Dict

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardHolds:
    """Two-stage card holds addressed by the hold ``id`` from ``create``."""

    def __init__(self, session, store_id):
        self.session = session
        self.store_id = store_id

    def _build_create(
        self, card_token, amount, invoice_id, expiry, *, split=None
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "card": {"token": card_token},
            "amount": int(amount),
            "store_id": self.store_id,
            "invoice_id": str(invoice_id),
            "expiry": int(expiry),
        }
        if split is not None:
            body["split"] = split
        return body

    def _build_debit(self, amount, split=None, ofd=None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"amount": int(amount)}
        if split is not None:
            body["split"] = split
        if ofd is not None:
            body["ofd"] = ofd
        return body

    @handle_exceptions
    def create(self, card_token, amount, invoice_id, expiry, **kwargs) -> Dict[str, Any]:
        body = self._build_create(card_token, amount, invoice_id, expiry, **kwargs)
        return self.session.post(MulticardEndpoints.HOLD, json_data=body)

    @handle_exceptions
    def confirm(self, hold_id, otp) -> Dict[str, Any]:
        return self.session.put(
            f"{MulticardEndpoints.HOLD}/{hold_id}", json_data={"otp": otp}
        )

    @handle_exceptions
    def debit(self, hold_id, amount, **kwargs) -> Dict[str, Any]:
        """Charge held funds (``amount`` may be less than held for a partial debit)."""
        body = self._build_debit(amount, **kwargs)
        return self.session.put(
            f"{MulticardEndpoints.HOLD}/{hold_id}/charge", json_data=body
        )

    @handle_exceptions
    def info(self, hold_id) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.HOLD}/{hold_id}")

    @handle_exceptions
    def cancel(self, hold_id) -> Dict[str, Any]:
        return self.session.delete(f"{MulticardEndpoints.HOLD}/{hold_id}")
