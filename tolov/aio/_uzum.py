"""Async Uzum payment gateway — inherits from sync, overrides HTTP calls."""
from typing import Dict, Any, Optional, Union

from tolov.core.http import AsyncHttpClient
from tolov.gateways.uzum.internal import UzumGatewayInternal as _SyncUzumInternal
from tolov.gateways.uzum.client import UzumGateway as _SyncUzumGateway
from tolov.gateways.uzum.constants import UzumNetworks, UzumEndpoints


class UzumGatewayInternal(_SyncUzumInternal):
    """Async Uzum internal — inherits _build_cancel_payment_request."""

    async def cancel_payment(
        self, id: str, amount: int, operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload, headers = self._build_cancel_payment_request(id, amount, operation_id)
        return await self.http_client.post(
            UzumEndpoints.REFUND, json_data=payload, headers=headers
        )


class UzumGateway(_SyncUzumGateway):
    """Async Uzum gateway — inherits create_payment and check_payment."""

    def __init__(
        self,
        service_id: str,
        is_test_mode: bool = False,
        terminal_id: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        from tolov.core.base import BasePaymentGateway

        BasePaymentGateway.__init__(self, is_test_mode)
        self.service_id = service_id
        self.terminal_id = terminal_id
        self.api_key = api_key

        self._internal = UzumGatewayInternal(
            service_id=service_id,
            is_test_mode=is_test_mode,
            terminal_id=terminal_id,
            api_key=api_key,
        )

        # Replace sync http_client with async one if credentials exist
        if terminal_id and api_key:
            api_url = UzumNetworks.TEST_NET if is_test_mode else UzumNetworks.PROD_NET
            headers = {
                "X-Terminal-Id": terminal_id,
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            }
            self._internal.http_client = AsyncHttpClient(
                base_url=api_url, headers=headers
            )

    async def cancel_payment(
        self, id: str, amount: int, operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._internal.cancel_payment(id, amount, operation_id)
