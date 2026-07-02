"""
Async FastAPI webhook handlers for Tolov (SQLAlchemy ``AsyncSession``).

Mirrors the sync handlers in ``internal.py``/``routes.py`` but operates on an
``AsyncSession`` and awaits all database I/O. Each handler subclasses its sync
counterpart to reuse the pure-compute helpers (auth / signature / amount checks)
and the overridable event hooks, and overrides every DB-touching method with an
``async`` version. Behaviour — protocol responses, error mapping, and the
exactly-once ``FOR UPDATE`` row locking — matches the sync handlers.

Usage:
    from sqlalchemy.ext.asyncio import AsyncSession
    from tolov.integrations.fastapi.aio import PaymeWebhookHandler

    @app.post("/payments/payme/webhook")
    async def payme_webhook(request: Request, db: AsyncSession = Depends(get_async_db)):
        handler = PaymeWebhookHandler(
            db=db, payme_id="...", payme_key="...", account_model=Order,
        )
        return await handler.handle_webhook(request)
"""
import hmac
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from loguru import logger

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tolov.core.exceptions import (
    PermissionDenied,
    InvalidAmount,
    TransactionNotFound,
    AccountNotFound,
    MethodNotFound,
    UnsupportedMethod,
    InvalidAccount,
)

from .models import PaymentTransaction
from .internal import (
    PaymeWebhookHandlerInternal as _SyncPayme,
    ClickWebhookHandlerInternal as _SyncClick,
    MulticardWebhookHandlerInternal as _SyncMulticard,
)

__all__ = [
    "PaymeWebhookHandler",
    "ClickWebhookHandler",
    "MulticardWebhookHandler",
]


def _json(payload: Dict[str, Any], status_code: int = 200) -> Response:
    """Build a JSON ``Response`` (async handlers return raw ``Response``)."""
    return Response(
        content=json.dumps(payload),
        media_type="application/json",
        status_code=status_code,
    )


def _rpc_result(request_id: Any, result: Any) -> Response:
    return _json({"jsonrpc": "2.0", "id": request_id, "result": result})


def _rpc_error(request_id: Any, code: int, message: str) -> Response:
    return _json(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
    )


class PaymeWebhookHandler(_SyncPayme):
    """Async Payme webhook handler. ``db`` is a SQLAlchemy ``AsyncSession``."""

    def __init__(
        self,
        db: AsyncSession,
        payme_id: str,
        payme_key: str,
        account_model: Any,
        account_field: str = "id",
        amount_field: str = "amount",
        one_time_payment: bool = True,
    ):
        super().__init__(
            db=db,
            payme_id=payme_id,
            payme_key=payme_key,
            account_model=account_model,
            account_field=account_field,
            amount_field=amount_field,
            one_time_payment=one_time_payment,
        )

    async def handle_webhook(self, request: Request) -> Response:
        """Handle a Payme JSON-RPC webhook request."""
        request_id = 0
        try:
            self._check_auth(request.headers.get("Authorization"))

            data = await request.json()
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id", 0)

            if method == "CheckPerformTransaction":
                result = await self._check_perform_transaction(params)
            elif method == "CreateTransaction":
                result = await self._create_transaction(params)
            elif method == "PerformTransaction":
                result = await self._perform_transaction(params)
            elif method == "CheckTransaction":
                result = await self._check_transaction(params)
            elif method == "CancelTransaction":
                result = await self._cancel_transaction(params)
            elif method == "GetStatement":
                result = await self._get_statement(params)
            else:
                return _rpc_error(request_id, -32601, f"Method not supported: {method}")

            return _rpc_result(request_id, result)

        except PermissionDenied:
            return _rpc_error(request_id, -32504, "permission denied")
        except (MethodNotFound, UnsupportedMethod) as e:
            return _rpc_error(request_id, -32601, str(e))
        except (AccountNotFound, InvalidAccount) as e:
            return _rpc_error(request_id, -31050, str(e))
        except (InvalidAmount, TransactionNotFound) as e:
            return _rpc_error(request_id, -31001, str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in Payme webhook: {e}")
            return _rpc_error(request_id, -32400, "Internal error")

    async def _find_account(self, params: Dict[str, Any]) -> Any:
        account_value = params.get("account", {}).get(self.account_field)
        if not account_value:
            raise AccountNotFound("Account not found in parameters")

        lookup_field = "id" if self.account_field == "order_id" else self.account_field

        if (
            lookup_field == "id"
            and isinstance(account_value, str)
            and account_value.isdigit()
        ):
            account_value = int(account_value)

        account = (
            (
                await self.db.execute(
                    select(self.account_model).filter_by(
                        **{lookup_field: account_value}
                    )
                )
            )
            .scalars()
            .first()
        )
        if not account:
            raise AccountNotFound(
                f"Account with {self.account_field}={account_value} not found"
            )
        return account

    async def _check_perform_transaction(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        account = await self._find_account(params)
        self._validate_amount(account, params.get("amount"))
        self.before_check_perform_transaction(params, account)
        return {"allow": True}

    async def _create_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        transaction_id = params.get("id")
        account = await self._find_account(params)
        amount = params.get("amount")

        self._validate_amount(account, amount)

        if self.one_time_payment:
            existing_transactions = (
                (
                    await self.db.execute(
                        select(PaymentTransaction).where(
                            PaymentTransaction.gateway == PaymentTransaction.PAYME,
                            PaymentTransaction.account_id == str(account.id),
                            PaymentTransaction.transaction_id != transaction_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            non_final_transactions = [
                t
                for t in existing_transactions
                if t.state
                not in [
                    PaymentTransaction.SUCCESSFULLY,
                    PaymentTransaction.CANCELLED,
                    PaymentTransaction.CANCELLED_DURING_INIT,
                ]
            ]

            if non_final_transactions:
                raise InvalidAccount(
                    f"Account with {self.account_field}={account.id} "
                    f"already has a pending transaction"
                )

        transaction = (
            (
                await self.db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.gateway == PaymentTransaction.PAYME,
                        PaymentTransaction.transaction_id == transaction_id,
                    )
                )
            )
            .scalars()
            .first()
        )

        if transaction:
            self.transaction_already_exists(params, transaction)
            create_time = transaction.extra_data.get("create_time", params.get("time"))
            return {
                "transaction": transaction.transaction_id,
                "state": transaction.state,
                "create_time": create_time,
            }

        transaction = PaymentTransaction(
            gateway=PaymentTransaction.PAYME,
            transaction_id=transaction_id,
            account_id=account.id,
            amount=Decimal(amount) / 100,
            state=PaymentTransaction.INITIATING,
            extra_data={
                "account_field": self.account_field,
                "account_value": params.get("account", {}).get(self.account_field),
                "create_time": params.get("time"),
                "raw_params": params,
            },
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)

        self.transaction_created(params, transaction, account)

        return {
            "transaction": transaction.transaction_id,
            "state": transaction.state,
            "create_time": params.get("time"),
        }

    async def _perform_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        transaction_id = params.get("id")

        # Lock the row (FOR UPDATE) so concurrent provider retries serialize
        # here and the success hook fires exactly once. populate_existing
        # refreshes the in-memory state read under the lock.
        transaction = (
            (
                await self.db.execute(
                    select(PaymentTransaction)
                    .where(
                        PaymentTransaction.gateway == PaymentTransaction.PAYME,
                        PaymentTransaction.transaction_id == transaction_id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        if transaction.state != PaymentTransaction.SUCCESSFULLY:
            await transaction.amark_as_paid(self.db)
            self.successfully_payment(params, transaction)

        return {
            "transaction": transaction.transaction_id,
            "state": transaction.state,
            "perform_time": int(transaction.performed_at.timestamp() * 1000)
            if transaction.performed_at
            else 0,
        }

    async def _check_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        transaction_id = params.get("id")

        transaction = (
            (
                await self.db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.gateway == PaymentTransaction.PAYME,
                        PaymentTransaction.transaction_id == transaction_id,
                    )
                )
            )
            .scalars()
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        self.check_transaction(params, transaction)

        create_time = transaction.extra_data.get(
            "create_time", int(transaction.created_at.timestamp() * 1000)
        )

        return {
            "transaction": transaction.transaction_id,
            "state": transaction.state,
            "create_time": create_time,
            "perform_time": int(transaction.performed_at.timestamp() * 1000)
            if transaction.performed_at
            else 0,
            "cancel_time": int(transaction.cancelled_at.timestamp() * 1000)
            if transaction.cancelled_at
            else 0,
            "reason": transaction.reason,
        }

    async def _cancel_response(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        reason = transaction.reason

        if reason is None:
            from tolov.gateways.payme.constants import PaymeCancelReason

            reason = PaymeCancelReason.REASON_FUND_RETURNED
            transaction.reason = reason
            await self.db.commit()
            await self.db.refresh(transaction)

        return {
            "transaction": transaction.transaction_id,
            "state": transaction.state,
            "cancel_time": int(transaction.cancelled_at.timestamp() * 1000)
            if transaction.cancelled_at
            else 0,
            "reason": reason,
        }

    async def _cancel_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        transaction_id = params.get("id")
        reason = params.get("reason")

        # Lock the row (FOR UPDATE) so concurrent cancels serialize and the
        # cancel hook fires exactly once.
        transaction = (
            (
                await self.db.execute(
                    select(PaymentTransaction)
                    .where(
                        PaymentTransaction.gateway == PaymentTransaction.PAYME,
                        PaymentTransaction.transaction_id == transaction_id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found",
            )

        cancelled_states = [
            PaymentTransaction.CANCELLED,
            PaymentTransaction.CANCELLED_DURING_INIT,
        ]
        if transaction.state in cancelled_states:
            if "reason" in params:
                reason = params.get("reason")

                if reason is None:
                    from tolov.gateways.payme.constants import PaymeCancelReason

                    reason = PaymeCancelReason.REASON_FUND_RETURNED

                if isinstance(reason, str) and reason.isdigit():
                    reason = int(reason)

                transaction.reason = reason

                extra_data = transaction.extra_data or {}
                extra_data["cancel_reason"] = reason
                transaction.extra_data = extra_data

                await self.db.commit()
                await self.db.refresh(transaction)

            return await self._cancel_response(transaction)

        reason = params.get("reason")
        await transaction.amark_as_cancelled(self.db, reason=reason)

        extra_data = transaction.extra_data or {}
        if "cancel_reason" not in extra_data:
            extra_data["cancel_reason"] = reason if reason is not None else 5
            transaction.extra_data = extra_data
            await self.db.commit()
            await self.db.refresh(transaction)

        self.cancelled_payment(params, transaction)

        return await self._cancel_response(transaction)

    async def _get_statement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from_date = params.get("from")
        to_date = params.get("to")

        from_datetime = (
            datetime.fromtimestamp(from_date / 1000)
            if from_date
            else datetime.fromtimestamp(0)
        )
        to_datetime = (
            datetime.fromtimestamp(to_date / 1000) if to_date else datetime.now()
        )

        transactions = (
            (
                await self.db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.gateway == PaymentTransaction.PAYME,
                        PaymentTransaction.created_at >= from_datetime,
                        PaymentTransaction.created_at <= to_datetime,
                    )
                )
            )
            .scalars()
            .all()
        )

        result = []
        for transaction in transactions:
            result.append(
                {
                    "id": transaction.transaction_id,
                    "time": int(transaction.created_at.timestamp() * 1000),
                    "amount": int(transaction.amount * 100),
                    "account": {self.account_field: transaction.account_id},
                    "state": transaction.state,
                    "create_time": transaction.extra_data.get(
                        "create_time", int(transaction.created_at.timestamp() * 1000)
                    ),
                    "perform_time": int(transaction.performed_at.timestamp() * 1000)
                    if transaction.performed_at
                    else 0,
                    "cancel_time": int(transaction.cancelled_at.timestamp() * 1000)
                    if transaction.cancelled_at
                    else 0,
                    "reason": transaction.reason,
                }
            )

        self.get_statement(params, result)
        return {"transactions": result}


class ClickWebhookHandler(_SyncClick):
    """Async Click webhook handler. ``db`` is a SQLAlchemy ``AsyncSession``."""

    def __init__(
        self,
        db: AsyncSession,
        service_id: str,
        secret_key: str,
        account_model: Any,
        commission_percent: float = 0.0,
        account_field: str = "id",
        one_time_payment: bool = True,
    ):
        super().__init__(
            db=db,
            service_id=service_id,
            secret_key=secret_key,
            account_model=account_model,
            commission_percent=commission_percent,
            account_field=account_field,
            one_time_payment=one_time_payment,
        )

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        try:
            form_data = await request.form()
            params = {key: form_data.get(key) for key in form_data}

            self._check_auth(params)

            click_trans_id = params.get("click_trans_id")
            merchant_trans_id = params.get("merchant_trans_id")
            amount = float(params.get("amount", 0))
            action = int(params.get("action", -1))
            error = int(params.get("error", 0))

            try:
                account = await self._find_account(merchant_trans_id)
            except Exception:
                logger.error(f"Account not found: {merchant_trans_id}")
                return {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "error": -5,
                    "error_note": "User not found",
                }

            try:
                expected = float(getattr(account, "amount", 0))
                self._validate_amount(amount, expected)
            except Exception as e:
                logger.error(f"Invalid amount: {e}")
                return {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "error": -2,
                    "error_note": str(e),
                }

            transaction = (
                (
                    await self.db.execute(
                        select(PaymentTransaction).where(
                            PaymentTransaction.gateway == PaymentTransaction.CLICK,
                            PaymentTransaction.transaction_id == click_trans_id,
                        )
                    )
                )
                .scalars()
                .first()
            )

            if transaction:
                if transaction.state == PaymentTransaction.SUCCESSFULLY:
                    self.transaction_already_exists(params, transaction)
                    return {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "merchant_prepare_id": transaction.id,
                        "error": 0,
                        "error_note": "Success",
                    }

                if transaction.state == PaymentTransaction.CANCELLED:
                    return {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "merchant_prepare_id": transaction.id,
                        "error": -9,
                        "error_note": "Transaction cancelled",
                    }

            if action == 0:  # Prepare
                transaction = PaymentTransaction(
                    gateway=PaymentTransaction.CLICK,
                    transaction_id=click_trans_id,
                    account_id=str(account.id),
                    amount=amount,
                    state=PaymentTransaction.INITIATING,
                    extra_data={
                        "raw_params": params,
                        "merchant_trans_id": merchant_trans_id,
                    },
                )

                self.db.add(transaction)
                await self.db.commit()
                await self.db.refresh(transaction)

                self.transaction_created(params, transaction, account)

                return {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_prepare_id": transaction.id,
                    "error": 0,
                    "error_note": "Success",
                }

            elif action == 1:  # Complete
                is_successful = error >= 0

                if not transaction:
                    transaction = PaymentTransaction(
                        gateway=PaymentTransaction.CLICK,
                        transaction_id=click_trans_id,
                        account_id=str(account.id),
                        amount=amount,
                        state=PaymentTransaction.INITIATING,
                        extra_data={
                            "raw_params": params,
                            "merchant_trans_id": merchant_trans_id,
                        },
                    )

                    self.db.add(transaction)
                    await self.db.commit()
                    await self.db.refresh(transaction)

                # Lock the row (FOR UPDATE) and refresh in-memory state so
                # concurrent completes serialize and the hook fires once.
                transaction = (
                    (
                        await self.db.execute(
                            select(PaymentTransaction)
                            .where(
                                PaymentTransaction.gateway == PaymentTransaction.CLICK,
                                PaymentTransaction.transaction_id == click_trans_id,
                            )
                            .with_for_update()
                            .execution_options(populate_existing=True)
                        )
                    )
                    .scalars()
                    .first()
                )

                if is_successful:
                    if transaction.state != PaymentTransaction.SUCCESSFULLY:
                        await transaction.amark_as_paid(self.db)
                        self.successfully_payment(params, transaction)
                elif transaction.state not in (
                    PaymentTransaction.CANCELLED,
                    PaymentTransaction.CANCELLED_DURING_INIT,
                ):
                    await transaction.amark_as_cancelled(
                        self.db, reason=f"Error code: {error}"
                    )
                    self.cancelled_payment(params, transaction)

                return {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_prepare_id": transaction.id,
                    "error": 0,
                    "error_note": "Success",
                }

            else:
                logger.error(f"Unsupported action: {action}")
                return {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "error": -3,
                    "error_note": "Action not found",
                }

        except Exception as e:
            logger.exception(f"Unexpected error in Click webhook: {e}")
            return {"error": -7, "error_note": "Internal error"}

    async def _find_account(self, merchant_trans_id: str) -> Any:
        account_value = merchant_trans_id

        if self.account_field == "id":
            if isinstance(account_value, str) and account_value.isdigit():
                account_value = int(account_value)

        account = (
            (
                await self.db.execute(
                    select(self.account_model).filter_by(
                        **{self.account_field: account_value}
                    )
                )
            )
            .scalars()
            .first()
        )
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with {self.account_field}={merchant_trans_id} not found",
            )

        return account


class MulticardWebhookHandler(_SyncMulticard):
    """Async Multicard success-callback handler. ``db`` is an ``AsyncSession``."""

    def __init__(
        self,
        db: AsyncSession,
        secret: str,
        account_model: Any,
        account_field: str = "id",
        store_id: Optional[int] = None,
    ):
        super().__init__(
            db=db,
            secret=secret,
            account_model=account_model,
            account_field=account_field,
            store_id=store_id,
        )

    async def handle_webhook(self, request: Request) -> Response:
        params = await request.json()

        received = params.get("sign") or ""
        if not hmac.compare_digest(str(received), self._expected_sign(params)):
            logger.warning(
                "Multicard webhook: bad signature for invoice {}",
                params.get("invoice_id"),
            )
            return _json({"success": False, "error": "invalid sign"}, status_code=403)

        if self.store_id is not None and str(params.get("store_id")) != str(
            self.store_id
        ):
            logger.warning(
                "Multicard webhook: store_id mismatch (got {}, expected {})",
                params.get("store_id"),
                self.store_id,
            )
            return _json({"success": False, "error": "store mismatch"}, status_code=403)

        await self._upsert(params)
        return _json({"success": True})

    async def _upsert(self, params: Dict[str, Any]) -> PaymentTransaction:
        account_id = params.get("invoice_id")
        if self.account_model is not None:
            account = await self._find_account(account_id)
            if account is not None:
                account_id = account.id

        await PaymentTransaction.acreate_transaction(
            db=self.db,
            gateway=PaymentTransaction.MULTICARD,
            transaction_id=params.get("uuid"),
            account_id=account_id,
            amount=Decimal(str(params.get("amount", 0))) / 100,
            extra_data={
                "card_token": params.get("card_token"),
                "card_pan": params.get("card_pan"),
                "ps": params.get("ps"),
                "receipt_url": params.get("receipt_url"),
                "phone": params.get("phone"),
                "billing_id": params.get("billing_id"),
                "payment_time": params.get("payment_time"),
                "raw_params": params,
            },
        )

        # Lock the row (FOR UPDATE) and refresh in-memory state so retried/
        # concurrent success callbacks fire the success hook exactly once.
        transaction = (
            (
                await self.db.execute(
                    select(PaymentTransaction)
                    .where(
                        PaymentTransaction.gateway == PaymentTransaction.MULTICARD,
                        PaymentTransaction.transaction_id == params.get("uuid"),
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .first()
        )
        if transaction.state != PaymentTransaction.SUCCESSFULLY:
            await transaction.amark_as_paid(self.db)
            self.successfully_payment(params, transaction)
        return transaction

    async def _find_account(self, value: Any) -> Any:
        lookup = "id" if self.account_field == "order_id" else self.account_field
        if lookup == "id" and isinstance(value, str) and value.isdigit():
            value = int(value)
        return (
            (
                await self.db.execute(
                    select(self.account_model).filter_by(**{lookup: value})
                )
            )
            .scalars()
            .first()
        )
