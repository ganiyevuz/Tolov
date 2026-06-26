"""Async Multicard gateway — inherits sync, overrides HTTP calls."""
from typing import Any, Dict, Optional, Union

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints
from tolov.gateways.multicard.session import AsyncMulticardSession
from tolov.gateways.multicard.invoices import MulticardInvoices as _SyncInvoices
from tolov.gateways.multicard.payments import MulticardPayments as _SyncPayments
from tolov.gateways.multicard.internal import MulticardGatewayInternal
from tolov.gateways.multicard.client import MulticardGateway as _SyncGateway


class MulticardInvoices(_SyncInvoices):
    """Async invoices — inherits ``_build_create``."""

    @handle_exceptions
    async def create(self, amount, invoice_id, callback_url, **kwargs) -> Dict[str, Any]:
        body = self._build_create(amount, invoice_id, callback_url, **kwargs)
        return await self.session.post(MulticardEndpoints.INVOICE, json_data=body)

    @handle_exceptions
    async def get(self, uuid) -> Dict[str, Any]:
        return await self.session.get(f"{MulticardEndpoints.INVOICE}/{uuid}")

    @handle_exceptions
    async def delete(self, uuid) -> Dict[str, Any]:
        return await self.session.delete(f"{MulticardEndpoints.INVOICE}/{uuid}")


class MulticardPayments(_SyncPayments):
    """Async payments — info + refund."""

    @handle_exceptions
    async def info(self, uuid) -> Dict[str, Any]:
        return await self.session.get(f"{MulticardEndpoints.PAYMENT}/{uuid}")

    @handle_exceptions
    async def refund(self, uuid) -> Dict[str, Any]:
        return await self.session.delete(
            f"{MulticardEndpoints.PAYMENT}/{uuid}", json_data={}
        )


class MulticardGateway(_SyncGateway):
    """Async Multicard gateway — async session + async sub-clients."""

    def _setup_clients(self):
        self.session = AsyncMulticardSession(
            application_id=self.application_id,
            secret=self.secret,
            is_test_mode=self.is_test_mode,
        )
        self._internal = MulticardGatewayInternal(
            session=self.session, store_id=self.store_id
        )
        self.invoices = MulticardInvoices(session=self.session, store_id=self.store_id)
        self.payments = MulticardPayments(session=self.session)
        self._internal.invoices = self.invoices
        self._internal.payments = self.payments

    @handle_exceptions
    async def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        callback_url: str = "",
        **kwargs,
    ) -> str:
        data = await self.invoices.create(
            amount=self._internal.to_tiyin(amount),
            invoice_id=id,
            callback_url=callback_url,
            return_url=return_url or None,
            **kwargs,
        )
        return data["checkout_url"]

    @handle_exceptions
    async def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        data = await self.payments.info(transaction_id)
        return self._internal.build_check_result(data)

    @handle_exceptions
    async def cancel_payment(
        self, transaction_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.payments.refund(transaction_id)
