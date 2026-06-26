"""Multicard payment gateway client (public, thin wrapper)."""
from typing import Any, Dict, Optional, Union

from tolov.core.base import BasePaymentGateway
from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.session import MulticardSession
from tolov.gateways.multicard.internal import MulticardGatewayInternal


class MulticardGateway(BasePaymentGateway):
    """Multicard gateway: invoice payment-page flow + ``.invoices`` / ``.payments``."""

    def __init__(self, application_id, secret, store_id, is_test_mode=False, **kwargs):
        super().__init__(is_test_mode)
        self.application_id = application_id
        self.secret = secret
        self.store_id = store_id
        self._setup_clients()

    def _setup_clients(self):
        self.session = MulticardSession(
            application_id=self.application_id,
            secret=self.secret,
            is_test_mode=self.is_test_mode,
        )
        self._internal = MulticardGatewayInternal(
            session=self.session, store_id=self.store_id
        )
        self.invoices = self._internal.invoices
        self.payments = self._internal.payments
        self.cards = self._internal.cards

    @handle_exceptions
    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        callback_url: str = "",
        **kwargs,
    ) -> str:
        """Create an invoice and return its ``checkout_url``. ``amount`` is in som."""
        data = self.invoices.create(
            amount=self._internal.to_tiyin(amount),
            invoice_id=id,
            callback_url=callback_url,
            return_url=return_url or None,
            **kwargs,
        )
        return data["checkout_url"]

    @handle_exceptions
    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        data = self.payments.info(transaction_id)
        return self._internal.build_check_result(data)

    @handle_exceptions
    def cancel_payment(
        self, transaction_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.payments.refund(transaction_id)
