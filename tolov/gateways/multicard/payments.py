"""Multicard payments sub-client (Phase 1: info + refund)."""
from typing import Any, Dict

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardPayments:
    """Read / refund payments by uuid."""

    def __init__(self, session):
        self.session = session

    @handle_exceptions
    def info(self, uuid) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.PAYMENT}/{uuid}")

    @handle_exceptions
    def refund(self, uuid) -> Dict[str, Any]:
        return self.session.delete(
            f"{MulticardEndpoints.PAYMENT}/{uuid}", json_data={}
        )
