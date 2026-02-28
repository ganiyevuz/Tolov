"""
Payme cards operations.
"""
from loguru import logger
from typing import Dict, Any

from tolov.core.http import HttpClient
from tolov.core.utils import handle_exceptions
from tolov.gateways.payme.constants import PaymeEndpoints




class PaymeCards:
    """
    Payme cards operations.

    This class provides methods for working with cards in the Payme payment system,
    including creating cards, verifying cards, and removing cards.
    """

    def __init__(self, http_client: HttpClient, payme_id: str):
        """
        Initialize the Payme cards component.

        Args:
            http_client: HTTP client for making requests
            payme_id: Payme merchant ID
        """
        self.http_client = http_client
        self.payme_id = payme_id

    def _get_auth_headers(self, language: str = 'uz') -> Dict[str, str]:
        """
        Get authentication headers for Payme API.

        Args:
            language: Language code (uz, ru, en)

        Returns:
            Dict containing authentication headers
        """
        headers = {
            "Accept-Language": language,
            "X-Auth": self.payme_id
        }
        return headers

    def _build_create_request(self, card_number, expire_date, save, **kwargs):
        phone = kwargs.get('phone')
        language = kwargs.get('language', 'uz')
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.CARDS_CREATE,
            "params": {
                "card": {
                    "number": card_number,
                    "expire": expire_date
                },
                "save": save
            },
            "id": 1
        }
        if phone:
            data["params"]["phone"] = phone
        headers = self._get_auth_headers(language)
        return data, headers

    @handle_exceptions
    def create(
        self,
        card_number: str,
        expire_date: str,
        save: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new card.

        Args:
            card_number: Card number
            expire_date: Card expiration date in format "MM/YY"
            save: Whether to save the card for future use
            **kwargs: Additional parameters
                - phone: Customer phone number
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing card creation response
        """
        data, headers = self._build_create_request(card_number, expire_date, save, **kwargs)
        return self.http_client.post(endpoint="", json_data=data, headers=headers)

    def _build_verify_request(self, token, code, **kwargs):
        language = kwargs.get('language', 'uz')
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.CARDS_VERIFY,
            "params": {
                "token": token,
                "code": code
            },
            "id": 1
        }
        headers = self._get_auth_headers(language)
        return data, headers

    @handle_exceptions
    def verify(
        self,
        token: str,
        code: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Verify a card with the verification code.

        Args:
            token: Card token received from create method
            code: Verification code sent to the card owner
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing card verification response
        """
        data, headers = self._build_verify_request(token, code, **kwargs)
        return self.http_client.post(endpoint="", json_data=data, headers=headers)

    def _build_check_request(self, token):
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.CARDS_CHECK,
            "params": {
                "token": token
            },
            "id": 1
        }
        headers = self._get_auth_headers()
        return data, headers

    @handle_exceptions
    def check(self, token: str) -> Dict[str, Any]:
        """
        Check if a card exists and is active.

        Args:
            token: Card token

        Returns:
            Dict containing card check response
        """
        data, headers = self._build_check_request(token)
        return self.http_client.post(endpoint="", json_data=data, headers=headers)

    def _build_remove_request(self, token):
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.CARDS_REMOVE,
            "params": {
                "token": token
            },
            "id": 1
        }
        headers = self._get_auth_headers()
        return data, headers

    @handle_exceptions
    def remove(self, token: str) -> Dict[str, Any]:
        """
        Remove a card.

        Args:
            token: Card token

        Returns:
            Dict containing card removal response
        """
        data, headers = self._build_remove_request(token)
        return self.http_client.post(endpoint="", json_data=data, headers=headers)

    def _build_get_verify_code_request(self, token, **kwargs):
        language = kwargs.get('language', 'uz')
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.CARDS_GET_VERIFY_CODE,
            "params": {
                "token": token
            },
            "id": 1
        }
        headers = self._get_auth_headers(language)
        return data, headers

    @handle_exceptions
    def get_verify_code(
        self,
        token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a new verification code for a card.

        Args:
            token: Card token
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing verification code response
        """
        data, headers = self._build_get_verify_code_request(token, **kwargs)
        return self.http_client.post(endpoint="", json_data=data, headers=headers)
