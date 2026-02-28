"""
Click merchant API operations.
"""
import hashlib
from typing import Dict, Any, Optional, Union

from tolov.core.http import HttpClient
from tolov.core.utils import handle_exceptions, generate_timestamp
from tolov.gateways.click.constants import ClickEndpoints


class ClickMerchantApi:
    """
    Click merchant API operations.

    This class provides methods for interacting with the Click merchant API,
    including checking payment status and canceling payments.
    """

    def __init__(
        self,
        http_client: HttpClient,
        service_id: str,
        merchant_user_id: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize the Click merchant API.

        Args:
            http_client: HTTP client for making requests
            service_id: Click service ID
            merchant_user_id: Click merchant user ID
            secret_key: Secret key for authentication
        """
        self.http_client = http_client
        self.service_id = service_id
        self.merchant_user_id = merchant_user_id
        self.secret_key = secret_key

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generate signature for Click API requests.

        Args:
            data: Request data

        Returns:
            Signature string
        """
        if not self.secret_key:
            return ""

        # Sort keys alphabetically
        sorted_data = {k: data[k] for k in sorted(data.keys())}

        # Create string to sign
        sign_string = ""
        for key, value in sorted_data.items():
            if key != "sign":
                sign_string += str(value)

        # Add secret key
        sign_string += self.secret_key

        # Generate signature
        return hashlib.md5(sign_string.encode("utf-8")).hexdigest()

    def _build_check_payment_request(self, id):
        data = {
            "service_id": self.service_id,
            "merchant_transaction_id": str(id),
            "request_id": str(generate_timestamp()),
        }
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/payment/status", data

    @handle_exceptions
    def check_payment(self, id: Union[int, str]) -> Dict[str, Any]:
        """
        Check payment status.

        Args:
            account_id: Account ID or order ID

        Returns:
            Dict containing payment status and details
        """
        endpoint, data = self._build_check_payment_request(id)
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_cancel_payment_request(self, id, reason=None):
        data = {
            "service_id": self.service_id,
            "merchant_transaction_id": str(id),
            "request_id": str(generate_timestamp()),
        }
        if reason:
            data["reason"] = reason
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/payment/cancel", data

    @handle_exceptions
    def cancel_payment(
        self, id: Union[int, str], reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel payment.

        Args:
            id: Account ID or order ID
            reason: Optional reason for cancellation

        Returns:
            Dict containing cancellation status and details
        """
        endpoint, data = self._build_cancel_payment_request(id, reason)
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_create_invoice_request(self, id, amount, **kwargs):
        description = kwargs.get("description", f"Payment for account {id}")
        phone = kwargs.get("phone")
        email = kwargs.get("email")
        expire_time = kwargs.get("expire_time", 60)

        data = {
            "service_id": self.service_id,
            "amount": float(amount),
            "merchant_transaction_id": str(id),
            "description": description,
            "request_id": str(generate_timestamp()),
            "expire_time": expire_time,
        }
        if phone:
            data["phone"] = phone
        if email:
            data["email"] = email
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/invoice/create", data

    @handle_exceptions
    def create_invoice(
        self, id: Union[int, str], amount: Union[int, float], **kwargs
    ) -> Dict[str, Any]:
        """
        Create an invoice.

        Args:
            amount: Payment amount
            account_id: Account ID or order ID
            **kwargs: Additional parameters
                - description: Payment description
                - phone: Customer phone number
                - email: Customer email
                - expire_time: Invoice expiration time in minutes

        Returns:
            Dict containing invoice details
        """
        endpoint, data = self._build_create_invoice_request(id, amount, **kwargs)
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_check_invoice_request(self, invoice_id):
        data = {
            "service_id": self.service_id,
            "invoice_id": invoice_id,
            "request_id": str(generate_timestamp()),
        }
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/invoice/status", data

    @handle_exceptions
    def check_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Check invoice status.

        Args:
            invoice_id: Invoice ID

        Returns:
            Dict containing invoice status and details
        """
        endpoint, data = self._build_check_invoice_request(invoice_id)
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_cancel_invoice_request(self, invoice_id, reason=None):
        data = {
            "service_id": self.service_id,
            "invoice_id": invoice_id,
            "request_id": str(generate_timestamp()),
        }
        if reason:
            data["reason"] = reason
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/invoice/cancel", data

    @handle_exceptions
    def cancel_invoice(
        self, invoice_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel invoice.

        Args:
            invoice_id: Invoice ID
            reason: Optional reason for cancellation

        Returns:
            Dict containing cancellation status and details
        """
        endpoint, data = self._build_cancel_invoice_request(invoice_id, reason)
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_card_token_request_request(self, card_number, expire_date, temporary):
        data = {
            "service_id": self.service_id,
            "card_number": card_number,
            "expire_date": expire_date,
            "temporary": temporary,
        }
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/card_token/request", data

    @handle_exceptions
    def card_token_request(
        self, card_number: str, expire_date: str, temporary: int = 0
    ) -> Dict[str, Any]:
        """
        Request a card token for card payment.

        Args:
            card_number: Card number (e.g., "5614681005030279")
            expire_date: Card expiration date (e.g., "0330" for March 2030)
            temporary: Whether the token is temporary (0 or 1)

        Returns:
            Dict containing card token and related information
        """
        endpoint, data = self._build_card_token_request_request(
            card_number, expire_date, temporary
        )
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_card_token_verify_request(self, card_token, sms_code):
        data = {
            "service_id": self.service_id,
            "card_token": card_token,
            "sms_code": int(sms_code),
        }
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/card_token/verify", data

    @handle_exceptions
    def card_token_verify(
        self, card_token: str, sms_code: Union[int, str]
    ) -> Dict[str, Any]:
        """
        Verify a card token with SMS code.

        Args:
            card_token: Card token from card_token_request
            sms_code: SMS code sent to the card holder

        Returns:
            Dict containing verification status and card information
        """
        endpoint, data = self._build_card_token_verify_request(card_token, sms_code)
        return self.http_client.post(endpoint=endpoint, json_data=data)

    def _build_card_token_payment_request(
        self, card_token, amount, transaction_parameter
    ):
        data = {
            "service_id": self.service_id,
            "card_token": card_token,
            "amount": float(amount),
            "transaction_parameter": transaction_parameter,
        }
        if self.secret_key:
            data["sign"] = self._generate_signature(data)
        return f"{ClickEndpoints.MERCHANT_API}/card_token/payment", data

    @handle_exceptions
    def card_token_payment(
        self, card_token: str, amount: Union[int, float], transaction_parameter: str
    ) -> Dict[str, Any]:
        """
        Make a payment using a verified card token.

        Args:
            card_token: Verified card token
            amount: Payment amount in som
            transaction_parameter: Unique transaction parameter

        Returns:
            Dict containing payment status and payment ID
        """
        endpoint, data = self._build_card_token_payment_request(
            card_token, amount, transaction_parameter
        )
        return self.http_client.post(endpoint=endpoint, json_data=data)
