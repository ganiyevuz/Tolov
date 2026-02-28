"""Async Octo payment gateway — inherits from sync, overrides HTTP calls."""
from loguru import logger
from typing import Dict, Any, Optional, Union

from tolov.core.http import AsyncHttpClient
from tolov.gateways.octo.internal import OctoGatewayInternal as _SyncOctoInternal
from tolov.gateways.octo.client import OctoGateway as _SyncOctoGateway


class OctoGatewayInternal(_SyncOctoInternal):
    """Async Octo internal — inherits _build_* methods."""

    async def create_payment(
        self,
        shop_transaction_id: Union[int, str],
        amount: Union[int, float],
        return_url: str,
        **kwargs
    ) -> Dict[str, Any]:
        endpoint, payload = self._build_create_payment_request(
            shop_transaction_id, amount, return_url, **kwargs
        )
        response = await self.http_client.post(endpoint=endpoint, json_data=payload)
        logger.info(
            "Octo prepare_payment response for %s: error=%s",
            shop_transaction_id,
            response.get("error"),
        )
        return response

    async def check_payment(self, shop_transaction_id: str) -> Dict[str, Any]:
        endpoint, payload = self._build_check_payment_request(shop_transaction_id)
        response = await self.http_client.post(endpoint=endpoint, json_data=payload)
        logger.info(
            "Octo check_payment response for %s: error=%s",
            shop_transaction_id,
            response.get("error"),
        )
        return response

    async def refund(
        self,
        octo_payment_uuid: str,
        amount: Union[int, float],
        shop_refund_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        endpoint, payload = self._build_refund_request(
            octo_payment_uuid, amount, shop_refund_id
        )
        response = await self.http_client.post(endpoint=endpoint, json_data=payload)
        logger.info(
            "Octo refund response for %s: error=%s",
            octo_payment_uuid,
            response.get("error"),
        )
        return response


class OctoGateway(_SyncOctoGateway):
    """Async Octo gateway — inherits create_payment/check_payment/cancel_payment structure."""

    def _setup_clients(self, url: str):
        self.http_client = AsyncHttpClient(base_url=url)
        self._internal = OctoGatewayInternal(
            octo_shop_id=self.octo_shop_id,
            octo_secret=self.octo_secret,
            notify_url=self.notify_url,
            is_test_mode=self.is_test_mode,
            http_client=self.http_client,
        )

    async def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        **kwargs
    ) -> str:
        response = await self._internal.create_payment(
            shop_transaction_id=id,
            amount=float(amount),
            return_url=return_url,
            **kwargs
        )
        data = response.get("data", {})
        return data.get("octo_pay_url", "")

    async def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        return await self._internal.check_payment(transaction_id)

    async def cancel_payment(
        self,
        transaction_id: str,
        amount: Union[int, float] = 0,
        reason: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if reason:
            logger.info("Octo refund reason: %s", reason)
        return await self._internal.refund(
            octo_payment_uuid=transaction_id, amount=float(amount), **kwargs
        )
