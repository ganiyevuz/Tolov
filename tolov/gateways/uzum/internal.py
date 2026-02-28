"""
Uzum payment gateway internal implementation.
This module contains the core business logic for Uzum Biller (open-service).
"""
import uuid
from loguru import logger
from typing import Dict, Any, Optional, Union

from tolov.core.http import HttpClient
from tolov.gateways.uzum.constants import UzumNetworks, UzumEndpoints, UzumStatus




class UzumGatewayInternal:
    """
    Internal Uzum gateway implementation with core business logic.
    Uses Uzum Biller (open-service) for payment URL generation.
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
        Initialize the internal Uzum gateway.

        Args:
            service_id: Uzum Service ID (serviceId parameter in Biller URL)
            is_test_mode: Whether to use the test environment
            terminal_id: Uzum Terminal ID for refund API (X-Terminal-Id header)
            api_key: Uzum API Key for refund API (X-API-Key header)
            **kwargs: Additional arguments
        """
        self.service_id = service_id
        self.is_test_mode = is_test_mode
        self.terminal_id = terminal_id
        self.api_key = api_key

        # Initialize HTTP client for refund API if credentials provided
        if terminal_id and api_key:
            api_url = UzumNetworks.TEST_NET if is_test_mode else UzumNetworks.PROD_NET
            headers = {
                "X-Terminal-Id": terminal_id,
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            self.http_client = HttpClient(base_url=api_url, headers=headers)
        else:
            self.http_client = None

    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = None,
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
        # Convert amount from som to tiyin (1 som = 100 tiyin)
        amount_tiyin = int(float(amount) * 100)

        service_id = kwargs.get("service_id", self.service_id)

        payment_url = f"{UzumNetworks.BILLER_URL}?serviceId={service_id}&order_id={id}&amount={amount_tiyin}"
        if return_url:
            payment_url += f"&redirectUrl={return_url}"

        return payment_url

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
        raise NotImplementedError("check_payment is not supported for Biller URL payments")

    def _build_cancel_payment_request(self, id, amount, operation_id=None):
        """Build ``(payload, headers)`` for cancel/refund."""
        if not self.http_client:
            raise ValueError("terminal_id and api_key are required for refund API")

        headers = {}
        if operation_id:
            headers["X-Operation-Id"] = operation_id
        else:
            headers["X-Operation-Id"] = str(uuid.uuid4())

        payload = {
            "orderId": str(id),
            "amount": int(amount)
        }
        return payload, headers

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
        payload, headers = self._build_cancel_payment_request(id, amount, operation_id)
        return self.http_client.post(UzumEndpoints.REFUND, json_data=payload, headers=headers)
