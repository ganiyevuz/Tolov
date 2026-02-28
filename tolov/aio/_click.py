"""Async Click payment gateway — inherits from sync, overrides HTTP calls."""
from typing import Dict, Any, Optional, Union

from tolov.core.http import AsyncHttpClient
from tolov.core.utils import handle_exceptions
from tolov.gateways.click.client import ClickGateway as _SyncClickGateway
from tolov.gateways.click.internal import ClickGatewayInternal
from tolov.gateways.click.merchant import ClickMerchantApi as _SyncClickMerchantApi


class ClickMerchantApi(_SyncClickMerchantApi):
    """Async Click merchant API — inherits __init__, helpers, and _build_* methods."""

    @handle_exceptions
    async def check_payment(self, id: Union[int, str]) -> Dict[str, Any]:
        endpoint, data = self._build_check_payment_request(id)
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def cancel_payment(
        self, id: Union[int, str], reason: Optional[str] = None
    ) -> Dict[str, Any]:
        endpoint, data = self._build_cancel_payment_request(id, reason)
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def create_invoice(
        self, id: Union[int, str], amount: Union[int, float], **kwargs
    ) -> Dict[str, Any]:
        endpoint, data = self._build_create_invoice_request(id, amount, **kwargs)
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def check_invoice(self, invoice_id: str) -> Dict[str, Any]:
        endpoint, data = self._build_check_invoice_request(invoice_id)
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def cancel_invoice(
        self, invoice_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        endpoint, data = self._build_cancel_invoice_request(invoice_id, reason)
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def card_token_request(
        self, card_number: str, expire_date: str, temporary: int = 0
    ) -> Dict[str, Any]:
        endpoint, data = self._build_card_token_request_request(
            card_number, expire_date, temporary
        )
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def card_token_verify(
        self, card_token: str, sms_code: Union[int, str]
    ) -> Dict[str, Any]:
        endpoint, data = self._build_card_token_verify_request(card_token, sms_code)
        return await self.http_client.post(endpoint=endpoint, json_data=data)

    @handle_exceptions
    async def card_token_payment(
        self, card_token: str, amount: Union[int, float], transaction_parameter: str
    ) -> Dict[str, Any]:
        endpoint, data = self._build_card_token_payment_request(
            card_token, amount, transaction_parameter
        )
        return await self.http_client.post(endpoint=endpoint, json_data=data)


class ClickGateway(_SyncClickGateway):
    """Async Click gateway — inherits create_payment (URL builder)."""

    def _setup_clients(self, url):
        self.http_client = AsyncHttpClient(base_url=url)
        self.merchant_api = ClickMerchantApi(
            http_client=self.http_client,
            service_id=self.service_id,
            merchant_user_id=self.merchant_user_id,
            secret_key=self.secret_key,
        )
        # Create _internal for inherited sync methods (create_payment is a URL builder, no HTTP)
        self._internal = ClickGatewayInternal(
            service_id=self.service_id,
            merchant_id=self.merchant_id,
            merchant_user_id=self.merchant_user_id,
            secret_key=self.secret_key,
            is_test_mode=self.is_test_mode,
            http_client=self.http_client,
            merchant_api=self.merchant_api,
        )

    @handle_exceptions
    async def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        account_id = ClickGatewayInternal.parse_transaction_id(transaction_id)
        payment_data = await self.merchant_api.check_payment(account_id)
        return ClickGatewayInternal.process_check_response(payment_data, transaction_id)

    @handle_exceptions
    async def cancel_payment(
        self, transaction_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        account_id = ClickGatewayInternal.parse_transaction_id(transaction_id)
        cancel_data = await self.merchant_api.cancel_payment(account_id, reason)
        return ClickGatewayInternal.process_cancel_response(cancel_data, transaction_id)

    async def card_token_request(
        self, card_number: str, expire_date: str, temporary: int = 0
    ) -> Dict[str, Any]:
        return await self.merchant_api.card_token_request(
            card_number, expire_date, temporary
        )

    async def card_token_verify(
        self, card_token: str, sms_code: Union[int, str]
    ) -> Dict[str, Any]:
        return await self.merchant_api.card_token_verify(card_token, sms_code)

    async def card_token_payment(
        self, card_token: str, amount: Union[int, float], transaction_parameter: str
    ) -> Dict[str, Any]:
        return await self.merchant_api.card_token_payment(
            card_token, amount, transaction_parameter
        )
