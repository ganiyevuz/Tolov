"""
Octo payment gateway internal implementation.
"""
import uuid
from loguru import logger
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from tolov.core.http import HttpClient
from tolov.gateways.octo.constants import (
    OctoEndpoints,
    OctoPaymentMethods,
)



class OctoGatewayInternal:
    """
    Internal implementation for Octo payment gateway.

    Handles direct API communication with Octo's ``prepare_payment``,
    status-check, and ``refund`` endpoints.
    """

    def __init__(
        self,
        octo_shop_id: int,
        octo_secret: str,
        notify_url: str = "",
        is_test_mode: bool = False,
        http_client: Optional[HttpClient] = None,
        **kwargs,
    ):
        self.octo_shop_id = octo_shop_id
        self.octo_secret = octo_secret
        self.notify_url = notify_url
        self.is_test_mode = is_test_mode
        self.http_client = http_client

    # ------------------------------------------------------------------
    # prepare_payment  (one-stage: auto_capture = True)
    # ------------------------------------------------------------------
    def create_payment(
        self,
        shop_transaction_id: Union[int, str],
        amount: Union[int, float],
        return_url: str,
        currency: str = "UZS",
        description: str = "",
        basket: Optional[List[Dict[str, Any]]] = None,
        payment_methods: Optional[List[Dict[str, str]]] = None,
        language: str = "uz",
        ttl: int = 15,
        user_data: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a one-stage payment via Octo ``prepare_payment``.

        Args:
            shop_transaction_id: Unique transaction identifier on merchant side.
            amount: Total payment amount.
            return_url: URL the user is redirected to after payment.
            currency: Payment currency (default ``UZS``).
            description: Payment description.
            basket: List of basket items for fiscalisation.
            payment_methods: Accepted payment methods (default: all).
            language: UI language for the payment page (``uz``, ``ru``, ``en``).
            ttl: Payment page time-to-live in minutes (default 15).
            user_data: Optional user info (``user_id``, ``phone``, ``email``).
            **kwargs: Extra fields forwarded to the request body.

        Returns:
            Dict with ``octo_pay_url``, ``octo_payment_UUID``, ``status``, etc.
        """
        init_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload: Dict[str, Any] = {
            "octo_shop_id": self.octo_shop_id,
            "octo_secret": self.octo_secret,
            "shop_transaction_id": str(shop_transaction_id),
            "auto_capture": True,
            "init_time": init_time,
            "test": self.is_test_mode,
            "total_sum": float(amount),
            "currency": currency,
            "description": description,
            "payment_methods": payment_methods or OctoPaymentMethods.ALL,
            "return_url": return_url,
            "language": language,
            "ttl": ttl,
        }

        if self.notify_url:
            payload["notify_url"] = self.notify_url

        if user_data:
            payload["user_data"] = user_data

        if basket:
            payload["basket"] = basket

        # Allow callers to pass additional/override fields
        payload.update(kwargs)

        response = self.http_client.post(
            endpoint=OctoEndpoints.PREPARE_PAYMENT,
            json_data=payload,
        )

        logger.info(
            "Octo prepare_payment response for %s: error=%s",
            shop_transaction_id,
            response.get("error"),
        )
        return response

    # ------------------------------------------------------------------
    # check_payment  (status inquiry via prepare_payment with 3 params)
    # ------------------------------------------------------------------
    def check_payment(self, shop_transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status by calling ``prepare_payment`` with
        only ``octo_shop_id``, ``octo_secret``, and ``shop_transaction_id``.

        Returns:
            Dict with ``status``, ``octo_payment_UUID``, etc.
        """
        payload = {
            "octo_shop_id": self.octo_shop_id,
            "octo_secret": self.octo_secret,
            "shop_transaction_id": str(shop_transaction_id),
        }

        response = self.http_client.post(
            endpoint=OctoEndpoints.PREPARE_PAYMENT,
            json_data=payload,
        )

        logger.info(
            "Octo check_payment response for %s: error=%s",
            shop_transaction_id,
            response.get("error"),
        )
        return response

    # ------------------------------------------------------------------
    # refund
    # ------------------------------------------------------------------
    def refund(
        self,
        octo_payment_uuid: str,
        amount: Union[int, float],
        shop_refund_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a completed payment.

        Args:
            octo_payment_uuid: The ``octo_payment_UUID`` from the original payment.
            amount: Amount to refund.
            shop_refund_id: Unique refund identifier (auto-generated if omitted).

        Returns:
            Dict with refund status and details.
        """
        payload = {
            "octo_shop_id": self.octo_shop_id,
            "octo_secret": self.octo_secret,
            "octo_payment_UUID": octo_payment_uuid,
            "shop_refund_id": shop_refund_id or str(uuid.uuid4()),
            "amount": float(amount),
        }

        response = self.http_client.post(
            endpoint=OctoEndpoints.REFUND,
            json_data=payload,
        )

        logger.info(
            "Octo refund response for %s: error=%s",
            octo_payment_uuid,
            response.get("error"),
        )
        return response
