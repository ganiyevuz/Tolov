"""
Paynet internal webhook handler.
"""
import json
from loguru import logger
from decimal import Decimal
from datetime import datetime

from django.views import View
from django.conf import settings
from django.db.transaction import atomic
from django.http import JsonResponse
from django.utils.module_loading import import_string

from tolov.core.exceptions import (
    PermissionDenied,
    InvalidAmount,
    TransactionNotFound,
    AccountNotFound,
    MethodNotFound,
    ServiceNotFound,
    TransactionAlreadyExists,
    AlreadyPaid,
)
from tolov.core.base import BasePaymentProcessor

from tolov.integrations.django.models import PaymentTransaction
from tolov.gateways.paynet.constants import PaynetErrors


class PaynetWebhook(BasePaymentProcessor, View):
    """
    Base Paynet webhook handler for Django.

    This class handles webhook requests from the Paynet payment system.
    You can extend this class and override the event methods to customize
    the behavior.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        paynet_settings = settings.TOLOV.get("PAYNET", {})

        self.paynet_username = paynet_settings.get("USERNAME", "")
        self.paynet_password = paynet_settings.get("PASSWORD", "")
        self.paynet_service_id = paynet_settings.get("SERVICE_ID", "")

        account_model_path = paynet_settings.get("ACCOUNT_MODEL")

        try:
            self.account_model = import_string(account_model_path)
        except ImportError:
            logger.error(
                "Could not import %s. Check TOLOV.PAYNET.ACCOUNT_MODEL setting.",
                account_model_path,
            )
            if account_model_path:
                raise ImportError(f"Import error: {account_model_path}") from None

        self.account_field = paynet_settings.get("ACCOUNT_FIELD", "id")
        self.amount_field = paynet_settings.get("AMOUNT_FIELD", "amount")
        self.account_info_fields = paynet_settings.get("ACCOUNT_INFO_FIELDS", ("id",))
        self.one_time_payment = paynet_settings.get("ONE_TIME_PAYMENT", True)

    def post(self, request, **_):
        """
        Handle POST requests from Paynet.
        """
        rpc_id = None
        try:
            # Check authorization
            self._check_auth(request)

            # Parse request data
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                # Paynet error code for JSON parsing error is -32700
                return self._error_response(
                    None, PaynetErrors.JSON_PARSING_ERROR, "Error parsing JSON."
                )

            if not isinstance(data, dict):
                return self._error_response(
                    None, PaynetErrors.INVALID_RPC_REQUEST, "Invalid RPC Request"
                )

            rpc_id = data.get("id")
            method = data.get("method")
            params = data.get("params", {})

            if not all(k in data for k in ("jsonrpc", "method", "id", "params")):
                return self._error_response(
                    rpc_id, PaynetErrors.INVALID_RPC_REQUEST, "Missing required fields"
                )

            # Process the request based on the method
            if method == "PerformTransaction":
                result = self._perform_transaction(params, rpc_id)
            elif method == "CheckTransaction":
                result = self._check_transaction(params)
            elif method == "CancelTransaction":
                result = self._cancel_transaction(params, rpc_id)
            elif method == "GetStatement":
                result = self._get_statement(params)
            elif method == "ChangePassword":
                result = "success"
            elif method == "GetInformation":
                result = self._get_information(params)
            else:
                raise MethodNotFound(f"method {method} is not supported")

            # Return the result
            return JsonResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})

        except PermissionDenied:
            response = self._error_response(
                rpc_id,
                PaynetErrors.INVALID_LOGIN_OR_PASSWORD,
                "Invalid login or password",
            )
            response.status_code = 401
            return response

        except MethodNotFound as e:
            return self._error_response(rpc_id, PaynetErrors.METHOD_NOT_FOUND, str(e))

        except ServiceNotFound as e:
            return self._error_response(rpc_id, PaynetErrors.SERVICE_NOT_FOUND, str(e))

        except AccountNotFound:
            return self._error_response(
                rpc_id, PaynetErrors.CLIENT_NOT_FOUND, "Клиент не найден"
            )

        except InvalidAmount as e:
            return self._error_response(rpc_id, PaynetErrors.INVALID_AMOUNT, str(e))

        except TransactionNotFound as e:
            return self._error_response(
                rpc_id, PaynetErrors.TRANSACTION_NOT_FOUND, str(e)
            )

        except TransactionAlreadyExists as e:
            return self._error_response(
                rpc_id, PaynetErrors.TRANSACTION_ALREADY_EXISTS, str(e)
            )

        except AlreadyPaid:
            return self._error_response(
                rpc_id, PaynetErrors.ALREADY_PAID, "Клиент не найден"
            )

        except Exception as e:
            logger.exception("Unexpected error in Paynet webhook: %s", e)
            return self._error_response(
                rpc_id, PaynetErrors.SYSTEM_ERROR, "System error"
            )

    def _check_auth(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        try:
            self.check_basic_auth(
                auth_header,
                expected_username=self.paynet_username,
                expected_password=self.paynet_password,
            )
        except PermissionDenied:
            # Re-raise to be caught by handle_webhook which maps it to error response
            raise
        except Exception as e:
            raise PermissionDenied("Invalid authentication format") from e

    def _validate_service_id(self, params):
        service_id = params.get("serviceId")
        if (
            service_id
            and self.paynet_service_id
            and str(service_id) != str(self.paynet_service_id)
        ):
            raise ServiceNotFound(f"Service {service_id} not found")

    def _error_response(self, rpc_id, code, message):
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": code, "message": message},
            },
            status=200,
        )

    def _find_account(self, params):
        """
        Find account by parameters.
        """
        # Paynet passes fields in params['fields']
        fields = params.get("fields", {})
        account_value = fields.get(self.account_field)

        if not account_value:
            # Try looking in top level just in case, but standard is fields
            account_value = params.get("account", {}).get(self.account_field)

        if not account_value:
            raise AccountNotFound("Account not found in parameters")

        try:
            lookup_field = (
                "id" if self.account_field == "order_id" else self.account_field
            )

            if (
                lookup_field == "id"
                and isinstance(account_value, str)
                and account_value.isdigit()
            ):
                account_value = int(account_value)

            lookup_kwargs = {lookup_field: account_value}
            account = self.account_model._default_manager.get(**lookup_kwargs)
            return account
        except self.account_model.DoesNotExist:
            raise AccountNotFound(
                f"Account with {self.account_field}={account_value} not found"
            ) from None

    def _perform_transaction(self, params, rpc_id):
        self._validate_service_id(params)
        transaction_id = params.get("transactionId")
        amount = params.get("amount")
        service_id = params.get("serviceId")

        account = self._find_account(params)

        # Check for one-time payment - if account already has a successful transaction
        if self.one_time_payment:
            existing_transaction = (
                PaymentTransaction._default_manager.filter(
                    gateway=PaymentTransaction.PAYNET,
                    account_id=account.id,
                    state=PaymentTransaction.SUCCESSFULLY,
                )
                .exclude(transaction_id=transaction_id)
                .first()
            )

            if existing_transaction:
                raise AlreadyPaid(
                    f"Account {account.id} already has a successful payment"
                )

        # Amount check
        # Convert account amount to tiyin (if stored in soum)
        # Verify strict amount match
        if hasattr(account, "amount"):
            account_amount_tiyin = int(
                account.amount * 100
            )  # Assuming account.amount is in soum
            request_amount_tiyin = int(amount)
            if account_amount_tiyin != request_amount_tiyin:
                raise InvalidAmount("Incorrect amount")

        # Check if transaction exists
        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYNET, transaction_id=transaction_id
            )
            raise TransactionAlreadyExists("Transaction already exists")
        except PaymentTransaction.DoesNotExist:
            pass

        # Create the transaction, then lock the row and finalize so concurrent
        # provider retries serialize and the success hook fires exactly once.
        transaction = PaymentTransaction.create_transaction(
            gateway=PaymentTransaction.PAYNET,
            transaction_id=transaction_id,
            account_id=account.id,
            amount=Decimal(amount) / 100,
            extra_data={
                "service_id": service_id,
                "rpc_id": rpc_id,
                "time": params.get("time"),
            },
        )

        with atomic():
            transaction = PaymentTransaction._default_manager.select_for_update().get(
                gateway=PaymentTransaction.PAYNET, transaction_id=transaction_id
            )
            if transaction.state != PaymentTransaction.SUCCESSFULLY:
                # Using / 100 for now.
                transaction.amount = Decimal(amount) / 100
                transaction.state = (
                    PaymentTransaction.SUCCESSFULLY
                )  # Paynet perform IS the payment execution usually
                transaction.save()

                transaction.mark_as_paid()

                self.successfully_payment(params, transaction)

        return {
            "providerTrnId": transaction.id,
            "timestamp": transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": {self.account_field: transaction.account_id},
        }

    def _check_transaction(self, params):
        self._validate_service_id(params)
        transaction_id = params.get("transactionId")
        service_id = params.get("serviceId")  # optional check

        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYNET, transaction_id=transaction_id
            )
        except PaymentTransaction.DoesNotExist:
            return {
                "transactionState": 3,  # Transaction not found
                "providerTrnId": 0,
                "timestamp": self._format_timestamp(datetime.now()),
            }

        # Map transaction states
        # 1 - Successful
        # 2 - Cancelled
        status = 1 if transaction.state == PaymentTransaction.SUCCESSFULLY else 2

        return {
            "transactionState": status,
            "providerTrnId": transaction.id,
            "timestamp": self._format_timestamp(transaction.updated_at),
        }

    def _cancel_transaction(self, params, rpc_id):
        self._validate_service_id(params)
        transaction_id = params.get("transactionId")

        try:
            # Lock the row so concurrent cancels serialize and the cancel hook
            # fires exactly once.
            with atomic():
                transaction = (
                    PaymentTransaction._default_manager.select_for_update().get(
                        gateway=PaymentTransaction.PAYNET, transaction_id=transaction_id
                    )
                )
                if transaction.state not in (
                    PaymentTransaction.CANCELLED,
                    PaymentTransaction.CANCELLED_DURING_INIT,
                ):
                    transaction.mark_as_cancelled()
                    self.cancelled_payment(params, transaction)
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound("Transaction not found")

        return {
            "providerTrnId": transaction.id,
            "timestamp": transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "transactionState": 2,  # Cancelled
        }

    def _get_statement(self, params):
        self._validate_service_id(params)
        date_from = params.get("dateFrom")
        date_to = params.get("dateTo")
        service_id = params.get("serviceId")

        # Parse dates (Paynet usually sends YYYY-MM-DD HH:MM:SS is likely string? Or timestamp?)
        # Original view code: `created_at__range=[serializer.validated_data["dateFrom"], serializer.validated_data["dateTo"]]`
        # We need to know the format. `GetStatementSerializer` handled it.
        # Assuming strings "YYYY-MM-DD HH:MM:SS"

        transactions = PaymentTransaction._default_manager.filter(
            gateway=PaymentTransaction.PAYNET,
            created_at__gte=date_from,
            created_at__lte=date_to,
        ).exclude(state=PaymentTransaction.CANCELLED)

        statements = [
            {
                "amount": int(tx.amount * 100),  # Return to Tiyin
                "providerTrnId": tx.id,
                "transactionId": tx.transaction_id,
                "timestamp": tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for tx in transactions
        ]

        return {"statements": statements}

    def _get_information(self, params):
        self._validate_service_id(params)
        account = self._find_account(params)

        # Check for one-time payment - if account already has a successful transaction
        if self.one_time_payment:
            existing_transaction = PaymentTransaction._default_manager.filter(
                gateway=PaymentTransaction.PAYNET,
                account_id=account.id,
                state=PaymentTransaction.SUCCESSFULLY,
            ).first()

            if existing_transaction:
                raise AlreadyPaid(
                    f"Account {account.id} already has a successful payment"
                )

        # Construct fields to return
        fields = {}
        for field in self.account_info_fields:
            if hasattr(account, field):
                fields[field] = getattr(account, field)
            else:
                # Try getting from dict if account is dict (unlikely for ORM)
                pass

        response = {
            "status": "0",  # Active
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fields": fields,
        }

        # Get additional check data from user implementation
        check_data = self.get_check_data(params, account)
        if check_data:
            # If user provides fields, merge them carefully
            if "fields" in check_data:
                response["fields"].update(check_data.pop("fields"))

            # Merge other top-level keys (e.g. balance, custom status keys if any)
            response.update(check_data)

        if "balance" in response:
            try:
                response["balance"] = int(float(response["balance"]))
            except (ValueError, TypeError):
                pass

        return response

    # Hooks
    def successfully_payment(self, params, transaction):
        pass

    def cancelled_payment(self, params, transaction):
        pass

    def get_check_data(self, params, account):
        pass

    def _format_timestamp(self, dt):
        """
        Format timestamp to "Fri Jan 30 10:21:18 UZT 2026"
        """
        if isinstance(dt, (int, float)):
            if dt == 0:
                dt = datetime.now()
            else:
                dt = datetime.fromtimestamp(dt)
        return dt.strftime("%a %b %d %H:%M:%S UZT %Y")
