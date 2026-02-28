"""
Click payment gateway internal implementation.
This module contains the actual business logic and will be compiled to .so
"""
from loguru import logger
from typing import Dict, Any, Optional, Union

from tolov.core.utils import handle_exceptions




class ClickGatewayInternal:
    """Internal implementation of Click gateway logic."""

    def __init__(self, service_id: str, merchant_id: str, merchant_user_id: Optional[str],
                 secret_key: Optional[str], is_test_mode: bool, http_client, merchant_api):

        self.service_id = service_id
        self.merchant_id = merchant_id
        self.merchant_user_id = merchant_user_id
        self.secret_key = secret_key
        self.is_test_mode = is_test_mode
        self.http_client = http_client
        self.merchant_api = merchant_api

    @handle_exceptions
    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        **kwargs
    ) -> str:
        """
        Create a payment using Click.

        Args:
            id: The account ID or order ID
            amount: The payment amount in som
            **kwargs: Additional parameters for the payment
                - description: Payment description
                - return_url: URL to return after payment
                - merchant_user_id: Merchant user ID

        Returns:
            Payment URL string
        """
        description = kwargs.get('description')
        return_url = kwargs.get('return_url')
        merchant_user_id = kwargs.get('merchant_user_id')

        payment_url = "https://my.click.uz/services/pay"
        payment_url += f"?service_id={self.service_id}"
        payment_url += f"&merchant_id={self.merchant_id}"
        payment_url += f"&amount={amount}"
        payment_url += f"&transaction_param={id}"

        if return_url:
            payment_url += f"&return_url={return_url}"

        if description:
            payment_url += f"&description={description}"

        if merchant_user_id:
            payment_url += f"&merchant_user_id={merchant_user_id}"

        return payment_url

    @staticmethod
    def parse_transaction_id(transaction_id):
        parts = transaction_id.split('_')
        if len(parts) < 3 or parts[0] != 'click':
            raise ValueError(f"Invalid transaction ID format: {transaction_id}")
        return parts[1]

    @staticmethod
    def process_check_response(payment_data, transaction_id):
        status = payment_data.get('status')
        status_mapping = {'success': 'paid', 'processing': 'waiting', 'failed': 'failed', 'cancelled': 'cancelled'}
        mapped_status = status_mapping.get(status, 'unknown')
        return {
            'transaction_id': transaction_id,
            'status': mapped_status,
            'amount': payment_data.get('amount'),
            'paid_at': payment_data.get('paid_at'),
            'created_at': payment_data.get('created_at'),
            'raw_response': payment_data
        }

    @staticmethod
    def process_cancel_response(cancel_data, transaction_id):
        return {
            'transaction_id': transaction_id,
            'status': 'cancelled',
            'cancelled_at': cancel_data.get('cancelled_at'),
            'raw_response': cancel_data
        }

    @handle_exceptions
    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Check payment status using Click merchant API."""
        account_id = self.parse_transaction_id(transaction_id)
        payment_data = self.merchant_api.check_payment(account_id)
        return self.process_check_response(payment_data, transaction_id)

    @handle_exceptions
    def cancel_payment(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel payment using Click merchant API."""
        account_id = self.parse_transaction_id(transaction_id)
        cancel_data = self.merchant_api.cancel_payment(account_id, reason)
        return self.process_cancel_response(cancel_data, transaction_id)

    @handle_exceptions
    def card_token_request(
        self,
        card_number: str,
        expire_date: str,
        temporary: int = 0
    ) -> Dict[str, Any]:
        """Request a card token for card payment."""
        return self.merchant_api.card_token_request(
            card_number=card_number,
            expire_date=expire_date,
            temporary=temporary
        )

    @handle_exceptions
    def card_token_verify(
        self,
        card_token: str,
        sms_code: Union[int, str]
    ) -> Dict[str, Any]:
        """Verify a card token with SMS code."""
        return self.merchant_api.card_token_verify(
            card_token=card_token,
            sms_code=sms_code
        )

    @handle_exceptions
    def card_token_payment(
        self,
        card_token: str,
        amount: Union[int, float],
        transaction_parameter: str
    ) -> Dict[str, Any]:
        """Make a payment using a verified card token."""
        return self.merchant_api.card_token_payment(
            card_token=card_token,
            amount=amount,
            transaction_parameter=transaction_parameter
        )
