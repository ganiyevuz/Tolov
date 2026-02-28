"""
Octo payment gateway client.
This is a thin wrapper that provides a clean interface but delegates to internal implementation.
"""
from loguru import logger
from typing import Dict, Any, Optional, Union, List

from tolov.core.http import HttpClient
from tolov.core.base import BasePaymentGateway
from tolov.gateways.octo.constants import OctoNetworks
from tolov.gateways.octo.internal import OctoGatewayInternal


class OctoGateway(BasePaymentGateway):
    """
    Octo payment gateway implementation.

    This class provides methods for interacting with the Octo payment gateway,
    including creating one-stage (auto_capture) payments, checking payment status,
    and processing refunds.

    Example::

        gateway = OctoGateway(
            octo_shop_id=123,
            octo_secret="your-secret-key",
            notify_url="https://example.com/octo/callback/",
        )

        result = gateway.create_payment(
            id="order-001",
            amount=50000,
            return_url="https://example.com/payment/complete/",
        )
        # Redirect user to result["data"]["octo_pay_url"]
    """

    def __init__(
        self,
        octo_shop_id: int,
        octo_secret: str,
        notify_url: str = "",
        is_test_mode: bool = False,
        **kwargs,
    ):
        """
        Initialize the Octo gateway.

        Args:
            octo_shop_id: Octo merchant shop ID.
            octo_secret: Octo secret key for authentication.
            notify_url: URL where Octo sends callback notifications.
            is_test_mode: When ``True``, transactions are created in test mode.
            **kwargs: Additional arguments (ignored, for backward compatibility).
        """
        super().__init__(is_test_mode)
        self.octo_shop_id = octo_shop_id
        self.octo_secret = octo_secret
        self.notify_url = notify_url

        # Octo uses the same URL; test mode is a request param
        url = OctoNetworks.TEST_NET if is_test_mode else OctoNetworks.PROD_NET
        self._setup_clients(url)

    def _setup_clients(self, url: str):
        """Initialize HTTP client and internal implementation."""
        self.http_client = HttpClient(base_url=url)
        self._internal = OctoGatewayInternal(
            octo_shop_id=self.octo_shop_id,
            octo_secret=self.octo_secret,
            notify_url=self.notify_url,
            is_test_mode=self.is_test_mode,
            http_client=self.http_client,
        )

    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        **kwargs,
    ) -> str:
        """
        Create a one-stage payment via Octo.

        Args:
            id: Unique order/transaction identifier on the merchant side.
            amount: Payment amount in som.
            return_url: URL the user is redirected to after payment.
            **kwargs: Additional parameters forwarded to ``prepare_payment``
                (e.g. ``currency``, ``description``, ``basket``,
                ``payment_methods``, ``language``, ``ttl``, ``user_data``).

        Returns:
            str: Octo payment URL for redirecting the user.
        """
        response = self._internal.create_payment(
            shop_transaction_id=id,
            amount=float(amount),
            return_url=return_url,
            **kwargs,
        )

        data = response.get("data", {})
        pay_url = data.get("octo_pay_url", "")

        return pay_url

    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status.

        Args:
            transaction_id: The ``shop_transaction_id`` used when creating the payment.

        Returns:
            Dict containing payment status and details.
        """
        return self._internal.check_payment(transaction_id)

    def cancel_payment(
        self,
        transaction_id: str,
        amount: Union[int, float] = 0,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Refund/cancel a completed payment.

        Args:
            transaction_id: The ``octo_payment_UUID`` from the original payment.
            amount: Amount to refund.
            reason: Optional reason for refund (not sent to Octo, for local logging).
            **kwargs: Extra arguments forwarded to the refund call.

        Returns:
            Dict containing refund status and details.
        """
        if reason:
            logger.info("Octo refund reason: %s", reason)

        return self._internal.refund(
            octo_payment_uuid=transaction_id,
            amount=float(amount),
            **kwargs,
        )
