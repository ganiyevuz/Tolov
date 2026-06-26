"""Multicard cards sub-client (form-based binding + token management).

The PCI-DSS-gated "Card Binding (API)" methods (adding a card with raw card
data) are intentionally not implemented.
"""
from typing import Any, Dict, Optional

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints


class MulticardCards:
    """Bind cards via the hosted form and manage the resulting tokens."""

    def __init__(self, session, store_id):
        self.session = session
        self.store_id = store_id

    def _build_bind(
        self,
        redirect_url,
        redirect_decline_url,
        callback_url,
        phone,
        *,
        pinfl=None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "store_id": self.store_id,
            "redirect_url": redirect_url,
            "redirect_decline_url": redirect_decline_url,
            "callback_url": callback_url,
            "phone": phone,
        }
        if pinfl is not None:
            body["pinfl"] = pinfl
        return body

    @handle_exceptions
    def bind(
        self,
        redirect_url,
        redirect_decline_url,
        callback_url,
        phone,
        *,
        pinfl: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Open a card-binding session. Returns ``{session_id, form_url}``."""
        body = self._build_bind(
            redirect_url, redirect_decline_url, callback_url, phone, pinfl=pinfl
        )
        return self.session.post(MulticardEndpoints.CARD_BIND, json_data=body)

    @handle_exceptions
    def check_binding(self, session_id) -> Dict[str, Any]:
        """Poll a binding session (15-min validity). Returns the card + token."""
        return self.session.get(f"{MulticardEndpoints.CARD_BIND}/{session_id}")

    @handle_exceptions
    def info_by_token(self, card_token) -> Dict[str, Any]:
        return self.session.get(f"{MulticardEndpoints.CARD}/{card_token}")

    @handle_exceptions
    def check_pinfl(self, pan, pinfl) -> Dict[str, Any]:
        """Check a card (Uzcard/Humo) belongs to a PINFL. data: bool|null."""
        return self.session.post(
            MulticardEndpoints.CARD_CHECK_PINFL,
            json_data={"pan": pan, "pinfl": pinfl},
        )

    @handle_exceptions
    def revoke_token(self, card_token) -> Dict[str, Any]:
        return self.session.delete(f"{MulticardEndpoints.CARD}/{card_token}")
