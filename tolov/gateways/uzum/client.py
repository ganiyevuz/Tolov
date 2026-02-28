"""
Uzum payment gateway client.
This client uses Uzum Biller (open-service) for payment URL generation.
"""
from loguru import logger
from typing import Dict, Any, Optional, Union

from tolov.core.base import BasePaymentGateway
from tolov.gateways.uzum.internal import UzumGatewayInternal



class UzumGateway(BasePaymentGateway):
    """
    Uzum payment gateway implementation.

    This class provides methods for creating payment URLs via Uzum Biller (open-service).
    Payment URL format: https://www.uzumbank.uz/open-service?serviceId=...&order_id=...&amount=...&redirectUrl=...
    """

    def __init__(
        self,
        service_id: str,
        is_test_mode: bool = False,
        terminal_id: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the Uzum gateway.

        Args:
            service_id: Uzum Service ID (serviceId parameter in Biller URL)
            is_test_mode: Whether to use the test environment
            terminal_id: Uzum Terminal ID for refund API (X-Terminal-Id header)
            api_key: Uzum API Key for refund API (X-API-Key header)
            **kwargs: Additional arguments
        """
        super().__init__(is_test_mode)
        self.service_id = service_id
        self.terminal_id = terminal_id
        self.api_key = api_key

        # Initialize internal implementation
        self._internal = UzumGatewayInternal(
            service_id=service_id,
            is_test_mode=is_test_mode,
            terminal_id=terminal_id,
            api_key=api_key
        )

    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str,
        **kwargs
    ) -> str:
        """
        Create a payment URL using Uzum Biller (open-service).

        Example URL:
            https://www.uzumbank.uz/open-service?serviceId=498624684&order_id=156&amount=10000000&redirectUrl=https://example.com

        Args:
            id: Order ID (order_id parameter)
            amount: Payment amount in som (will be converted to tiyin)
            return_url: URL to redirect after payment (redirectUrl parameter)
            **kwargs: Optional parameters:
                - service_id: Uzum service ID (overrides self.service_id if provided)

        Returns:
            str: Payment URL for redirecting user to Uzum payment page
        """
        return self._internal.create_payment(id, amount, return_url, **kwargs)

    def check_payment(self, id: str) -> Dict[str, Any]:
        """
        Check payment status by order ID.

        Note: This method is not supported for Biller URL payments.
        Use webhook callbacks to track payment status.

        Args:
            id: The order ID
        
        Returns:
            Dict containing payment status
        """
        return self._internal.check_payment(id)

    def cancel_payment(
        self,
        id: str,
        amount: int,
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund/Cancel payment using Uzum Checkout API.

        Args:
            id: The order ID or Invoice ID to refund
            amount: Amount to refund in tiyin
            operation_id: Optional unique operation ID (X-Operation-Id header)
        
        Returns:
            Dict containing refund response
        """
        return self._internal.cancel_payment(id, amount, operation_id)
