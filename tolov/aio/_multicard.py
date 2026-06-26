"""Async Multicard gateway — inherits sync, overrides HTTP calls."""
from typing import Any, Dict, Optional, Union

from tolov.core.utils import handle_exceptions
from tolov.gateways.multicard.constants import MulticardEndpoints
from tolov.gateways.multicard.session import AsyncMulticardSession
from tolov.gateways.multicard.invoices import MulticardInvoices as _SyncInvoices
from tolov.gateways.multicard.payments import MulticardPayments as _SyncPayments
from tolov.gateways.multicard.cards import MulticardCards as _SyncCards
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
    """Async payments — reuses the sync ``_build_*`` helpers."""

    @handle_exceptions
    async def info(self, uuid) -> Dict[str, Any]:
        return await self.session.get(f"{MulticardEndpoints.PAYMENT}/{uuid}")

    @handle_exceptions
    async def create_by_token(self, card_token, amount, invoice_id, **kwargs) -> Dict[str, Any]:
        body = self._build_create_by_token(card_token, amount, invoice_id, **kwargs)
        return await self.session.post(MulticardEndpoints.PAYMENT, json_data=body)

    @handle_exceptions
    async def app_pay(self, payment_system, amount, invoice_id, **kwargs) -> Dict[str, Any]:
        body = self._build_app_pay(payment_system, amount, invoice_id, **kwargs)
        return await self.session.post(MulticardEndpoints.PAYMENT, json_data=body)

    @handle_exceptions
    async def confirm(self, uuid, otp=None, *, debit_available=None) -> Dict[str, Any]:
        body = self._build_confirm(otp, debit_available)
        return await self.session.put(
            f"{MulticardEndpoints.PAYMENT}/{uuid}", json_data=body
        )

    @handle_exceptions
    async def refund(self, uuid) -> Dict[str, Any]:
        return await self.session.delete(
            f"{MulticardEndpoints.PAYMENT}/{uuid}", json_data={}
        )

    @handle_exceptions
    async def partial_refund(self, uuid, refund_amount, ofd, *, card_pan=None) -> Dict[str, Any]:
        body = self._build_partial_refund(refund_amount, ofd, card_pan)
        return await self.session.delete(
            f"{MulticardEndpoints.PAYMENT}/{uuid}/partial", json_data=body
        )

    @handle_exceptions
    async def send_fiscal(self, uuid, url, *, is_refund=None) -> Dict[str, Any]:
        body = self._build_fiscal(url, is_refund)
        return await self.session.patch(
            f"{MulticardEndpoints.PAYMENT}/{uuid}/fiscal", json_data=body
        )


class MulticardCards(_SyncCards):
    """Async cards — inherits ``_build_bind``."""

    @handle_exceptions
    async def bind(
        self, redirect_url, redirect_decline_url, callback_url, phone, *, pinfl=None
    ) -> Dict[str, Any]:
        body = self._build_bind(
            redirect_url, redirect_decline_url, callback_url, phone, pinfl=pinfl
        )
        return await self.session.post(MulticardEndpoints.CARD_BIND, json_data=body)

    @handle_exceptions
    async def check_binding(self, session_id) -> Dict[str, Any]:
        return await self.session.get(f"{MulticardEndpoints.CARD_BIND}/{session_id}")

    @handle_exceptions
    async def info_by_token(self, card_token) -> Dict[str, Any]:
        return await self.session.get(f"{MulticardEndpoints.CARD}/{card_token}")

    @handle_exceptions
    async def check_pinfl(self, pan, pinfl) -> Dict[str, Any]:
        return await self.session.post(
            MulticardEndpoints.CARD_CHECK_PINFL,
            json_data={"pan": pan, "pinfl": pinfl},
        )

    @handle_exceptions
    async def revoke_token(self, card_token) -> Dict[str, Any]:
        return await self.session.delete(f"{MulticardEndpoints.CARD}/{card_token}")


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
        self.payments = MulticardPayments(session=self.session, store_id=self.store_id)
        self.cards = MulticardCards(session=self.session, store_id=self.store_id)
        self._internal.invoices = self.invoices
        self._internal.payments = self.payments
        self._internal.cards = self.cards

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
