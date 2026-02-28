"""
Paynet payment gateway internal implementation.
This module contains the actual business logic and will be compiled to .so
"""
from loguru import logger
from typing import Union, Optional


class PaynetGatewayInternal:
    """Internal implementation of Paynet gateway logic."""

    def __init__(self, merchant_id: Union[str, int], is_test_mode: bool):
        self.merchant_id = str(merchant_id)
        self.is_test_mode = is_test_mode

    def generate_pay_link(
        self, id: Union[int, str], amount: Optional[Union[int, float, str]] = None
    ) -> str:
        """
        Generate a payment link for Paynet.

        Args:
            id: Unique identifier for the account/payment (c parameter)
            amount: Payment amount in tiyin (optional, a parameter)

        Returns:
            Paynet payment URL with merchant ID, account ID, and optional amount
        """
        # Paynet URL structure: https://app.paynet.uz/?m={merchant_id}&c={account_id}&a={amount}
        base_url = "https://app.paynet.uz"
        url = f"{base_url}/?m={self.merchant_id}&c={id}"
        if amount is not None:
            url += f"&a={int(amount)}"
        return url
