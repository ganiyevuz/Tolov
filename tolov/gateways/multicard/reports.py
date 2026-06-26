"""Multicard reporting sub-client (read-only).

Application/wallet info, recipient (merchant-account) requisites, and the
processed-payment / payout registries. Dates are ``YYYY-mm-dd HH:MM:SS`` (GMT+5).
"""
from typing import Any, Dict, Optional

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardReports:
    """Read-only application, recipient, and registry lookups."""

    def __init__(self, session, store_id=None):
        self.session = session
        self.store_id = store_id

    def _history_params(self, start_date, end_date, offset, limit, only_status):
        params: Dict[str, Any] = {
            "offset": offset,
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date,
        }
        if only_status is not None:
            params["only_status"] = only_status
        return params

    @handle_exceptions
    def app_info(self) -> Dict[str, Any]:
        return self.session.get(MulticardEndpoints.APPLICATION)

    @handle_exceptions
    def recipient_details(self, recipient) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.MERCHANT_ACCOUNT}/{recipient}")

    @handle_exceptions
    def payment_registry(
        self, start_date, end_date, *, offset=0, limit=50,
        only_status: Optional[str] = None, store_id=None
    ) -> Dict[str, Any]:
        store_id = store_id if store_id is not None else self.store_id
        params = self._history_params(start_date, end_date, offset, limit, only_status)
        return self.session.get(
            f"{MulticardEndpoints.STORE}/{store_id}/history", params=params
        )

    @handle_exceptions
    def payout_history(
        self, start_date, end_date, *, offset=0, limit=50,
        only_status: Optional[str] = None, store_id=None
    ) -> Dict[str, Any]:
        store_id = store_id if store_id is not None else self.store_id
        params = self._history_params(start_date, end_date, offset, limit, only_status)
        return self.session.get(
            f"{MulticardEndpoints.STORE}/{store_id}/credit-history", params=params
        )
