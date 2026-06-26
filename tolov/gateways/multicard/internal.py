"""Multicard gateway internal logic (pyarmor-split)."""
from typing import Any, Dict, Optional, Union

from tolov.gateways.multicard.constants import STATUS_TO_STATE
from tolov.gateways.multicard.invoices import MulticardInvoices
from tolov.gateways.multicard.payments import MulticardPayments
from tolov.gateways.multicard.cards import MulticardCards
from tolov.gateways.multicard.holds import MulticardHolds


class MulticardGatewayInternal:
    """Core Multicard logic shared by sync and async gateways."""

    def __init__(self, session, store_id):
        self.session = session
        self.store_id = store_id
        self.invoices = MulticardInvoices(session=session, store_id=store_id)
        self.payments = MulticardPayments(session=session, store_id=store_id)
        self.cards = MulticardCards(session=session, store_id=store_id)
        self.holds = MulticardHolds(session=session, store_id=store_id)

    @staticmethod
    def map_status(status: Optional[str]) -> int:
        return STATUS_TO_STATE.get(status, 1)

    @staticmethod
    def to_tiyin(amount: Union[int, float, str]) -> int:
        return int(float(amount) * 100)

    def build_check_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payment = data.get("payment") if isinstance(data, dict) else None
        status = (payment or data or {}).get("status")
        return {"status": status, "state": self.map_status(status), "data": data}
