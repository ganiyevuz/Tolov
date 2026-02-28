"""Async Payme payment gateway — inherits from sync, overrides HTTP calls."""
from typing import Dict, Any, Optional, Union

from tolov.core.http import AsyncHttpClient
from tolov.core.utils import handle_exceptions
from tolov.gateways.payme.cards import PaymeCards as _SyncPaymeCards
from tolov.gateways.payme.receipts import PaymeReceipts as _SyncPaymeReceipts
from tolov.gateways.payme.client import PaymeGateway as _SyncPaymeGateway
from tolov.gateways.payme.internal import PaymeGatewayInternal


class PaymeCards(_SyncPaymeCards):
    """Async Payme cards — inherits __init__, helpers, and _build_* methods."""

    @handle_exceptions
    async def create(
        self,
        card_number: str,
        expire_date: str,
        save: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        data, headers = self._build_create_request(card_number, expire_date, save, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def verify(self, token: str, code: str, **kwargs) -> Dict[str, Any]:
        data, headers = self._build_verify_request(token, code, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def check(self, token: str) -> Dict[str, Any]:
        data, headers = self._build_check_request(token)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def remove(self, token: str) -> Dict[str, Any]:
        data, headers = self._build_remove_request(token)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def get_verify_code(self, token: str, **kwargs) -> Dict[str, Any]:
        data, headers = self._build_get_verify_code_request(token, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)


class PaymeReceipts(_SyncPaymeReceipts):
    """Async Payme receipts — inherits __init__, helpers, and _build_* methods."""

    @handle_exceptions
    async def create(self, amount: int, account: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        data, headers = self._build_create_request(amount, account, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def pay(self, receipt_id: str, token: str, **kwargs) -> Dict[str, Any]:
        data, headers = self._build_pay_request(receipt_id, token, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def send(self, receipt_id: str, phone: str, **kwargs) -> Dict[str, Any]:
        data, headers = self._build_send_request(receipt_id, phone, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def check(self, receipt_id: str, **kwargs) -> Dict[str, Any]:
        data, headers = self._build_check_request(receipt_id, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def cancel(
        self,
        receipt_id: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        data, headers = self._build_cancel_request(receipt_id, reason, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)

    @handle_exceptions
    async def get(self, receipt_id: str, **kwargs) -> Dict[str, Any]:
        data, headers = self._build_get_request(receipt_id, **kwargs)
        return await self.http_client.post(endpoint="", json_data=data, headers=headers)


class PaymeGateway(_SyncPaymeGateway):
    """Async Payme gateway — inherits generate_pay_link and create_payment."""

    def _setup_clients(self, url):
        self.http_client = AsyncHttpClient(base_url=url)
        self.cards = PaymeCards(http_client=self.http_client, payme_id=self.payme_id)
        self.receipts = PaymeReceipts(
            http_client=self.http_client,
            payme_id=self.payme_id,
            payme_key=self.payme_key,
        )
        # Create _internal for inherited sync methods (generate_pay_link, create_payment)
        # These methods are pure computation (no HTTP), so a sync internal is fine.
        self._internal = PaymeGatewayInternal(
            payme_id=self.payme_id,
            payme_key=self.payme_key,
            fallback_id=self.fallback_id,
            is_test_mode=self.is_test_mode,
            http_client=self.http_client,
            cards=self.cards,
            receipts=self.receipts,
        )

    @handle_exceptions
    async def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        receipt_data = await self.receipts.check(receipt_id=transaction_id)
        return PaymeGatewayInternal.process_check_response(receipt_data, transaction_id)

    @handle_exceptions
    async def cancel_payment(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        receipt_data = await self.receipts.cancel(
            receipt_id=transaction_id,
            reason=reason or "Cancelled by merchant"
        )
        return PaymeGatewayInternal.process_cancel_response(receipt_data, transaction_id)
