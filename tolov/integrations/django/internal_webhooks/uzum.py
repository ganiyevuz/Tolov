"""
Uzum internal webhook handler.
"""
import json
import base64
from loguru import logger

from decimal import Decimal
from datetime import datetime

from django.views import View
from django.conf import settings
from django.http import JsonResponse
from django.utils.module_loading import import_string

from tolov.gateways.uzum.constants import UzumStatus
from tolov.core.exceptions import (
    AccountNotFound,
    TransactionNotFound,
    PermissionDenied,
    InvalidServiceId,
    PaymentAlreadyMade,
    TransactionCancelled,
)
from tolov.core.base import BasePaymentProcessor
from tolov.integrations.django.models import PaymentTransaction


class UzumWebhook(BasePaymentProcessor, View):
    """
    Base Uzum webhook handler for Django.

    Handles requests from Uzum Biller API.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        uzum_settings = settings.TOLOV.get("UZUM", {})

        # For Biller API (webhooks) - uses Basic Auth with username and password
        self.username = uzum_settings.get("USERNAME")
        self.password = uzum_settings.get("PASSWORD")
        self.service_id = uzum_settings.get("SERVICE_ID")  # Default/placeholder

        account_model_path = uzum_settings.get("ACCOUNT_MODEL")

        try:
            self.account_model = import_string(account_model_path)
        except ImportError:
            logger.error(
                "Could not import %s. Check TOLOV.UZUM.ACCOUNT_MODEL setting.",
                account_model_path,
            )
            if account_model_path:
                raise ImportError(f"Import error: {account_model_path}") from None

        self.account_field = uzum_settings.get("ACCOUNT_FIELD", "id")
        self.amount_field = uzum_settings.get("AMOUNT_FIELD", "amount")
        self.one_time_payment = uzum_settings.get("ONE_TIME_PAYMENT", True)

    def _error_response(self, error_code, request_data=None):
        """
        Generate error response in Uzum format.
        """
        timestamp = int(datetime.now().timestamp() * 1000)

        # Try to get serviceId from request if available,
        # otherwise use configured service_id or default
        service_id = self.service_id
        if request_data and "serviceId" in request_data:
            service_id = request_data["serviceId"]

        return {
            "serviceId": service_id,
            "timestamp": timestamp,
            "status": UzumStatus.FAILED,
            "errorCode": str(error_code),
        }

    def post(self, request, action, **_):
        """
        Handle POST requests from Uzum.
        Actions are part of the URL: /check, /create, etc.
        """
        data = {}
        try:
            # Parse request data first to be able to use it in error response
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                return JsonResponse(
                    self._error_response("10002"), status=400  # JSON Parsing Error
                )

            # Check authorization
            self._check_auth(request)

            # Validate service ID
            self._check_service_id(data)

            if action == "check":
                result = self._handle_check(data)
            elif action == "create":
                result = self._handle_create(data)
            elif action == "confirm":
                result = self._handle_confirm(data)
            elif action == "reverse":
                result = self._handle_reverse(data)
            elif action == "status":
                result = self._handle_status(data)
            else:
                return JsonResponse(
                    self._error_response("10003", data), status=400  # Invalid Operation
                )

            return JsonResponse(result)

        except PermissionDenied:
            return JsonResponse(
                self._error_response("10001", data), status=400  # Access Denied
            )
        except InvalidServiceId:
            return JsonResponse(
                self._error_response("10006", data), status=400  # Invalid Service ID
            )
        except AccountNotFound:
            return JsonResponse(
                self._error_response("10007", data),  # Account/Attribute Not Found
                status=400,
            )
        except PaymentAlreadyMade:
            return JsonResponse(
                self._error_response("10008", data), status=400  # Payment Already Made
            )
        except TransactionCancelled:
            return JsonResponse(
                self._error_response("10009", data), status=400  # Payment Cancelled
            )
        except TransactionNotFound:
            return JsonResponse(
                self._error_response("10009", data), status=400  # Transaction not found
            )
        except Exception as e:
            logger.exception(f"Uzum webhook error: {e}")
            return JsonResponse(
                self._error_response("99999", data), status=400  # Internal Error
            )

    def _check_auth(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        try:
            self.check_basic_auth(
                auth_header,
                expected_username=self.username,
                expected_password=self.password,
            )
        except PermissionDenied:
            # Re-raise to be handled by exception handler
            raise
        except Exception as e:
            logger.error(f"Uzum auth failed for username: {self.username}")
            raise PermissionDenied("Authentication error") from e

    def _check_service_id(self, data):
        """Validate service ID from request matches configured service ID."""
        request_service_id = data.get("serviceId")

        if request_service_id is None:
            logger.error("Uzum webhook: Missing serviceId in request")
            raise InvalidServiceId("Missing service ID")

        if self.service_id and int(request_service_id) != int(self.service_id):
            logger.error(
                f"Uzum webhook: Invalid serviceId. Expected {self.service_id}, got {request_service_id}"
            )
            raise InvalidServiceId("Invalid service ID")

    def _find_account(self, params):
        """Find account by parameters."""
        # Try to get account value from params using configured field name
        # Also check common field names: 'account', 'orderId', 'order_id'
        account_value = params.get(self.account_field)

        if not account_value:
            account_value = params.get("account")

        if not account_value:
            account_value = params.get("orderId")

        if not account_value:
            account_value = params.get("order_id")

        if not account_value:
            raise AccountNotFound("Account identifier not found")

        # Handle lookup similar to Payme
        lookup_field = "id" if self.account_field == "order_id" else self.account_field

        if (
            lookup_field == "id"
            and isinstance(account_value, str)
            and account_value.isdigit()
        ):
            account_value = int(account_value)

        lookup_kwargs = {lookup_field: account_value}
        try:
            return self.account_model._default_manager.get(**lookup_kwargs)
        except self.account_model.DoesNotExist:
            raise AccountNotFound("Account not found")

    def _handle_check(self, data):
        """
        Request: { "serviceId": ..., "params": { "orderId": ... } }
        Response: { "serviceId": ..., "timestamp": ..., "status": "OK", "data": { ... } }
        """
        params = data.get("params", {})
        if not params:
            raise AccountNotFound("Missing params")

        account = self._find_account(params)

        extra_data = self.get_check_data(params, account) or {}

        response_data = {"account": {"value": str(account.id)}}
        response_data.update(extra_data)

        timestamp = int(datetime.now().timestamp() * 1000)
        service_id = data.get("serviceId", self.service_id)

        return {
            "serviceId": service_id,
            "timestamp": timestamp,
            "status": UzumStatus.OK,
            "data": response_data,
        }

    def _handle_create(self, data):
        """
        Request: { "transId": "...", "amount": 1000, "params": ... }
        """
        trans_id = data.get("transId")
        service_id = data.get("serviceId", self.service_id)
        amount = data.get("amount")  # in tiyins
        params = data.get("params", {})

        account = self._find_account(params)

        # Check for one-time payment - if account already has a successful transaction
        if self.one_time_payment:
            existing_transaction = (
                PaymentTransaction.objects.filter(
                    gateway=PaymentTransaction.UZUM,
                    account_id=str(account.id),
                    state=PaymentTransaction.SUCCESSFULLY,
                )
                .exclude(transaction_id=trans_id)
                .first()
            )

            if existing_transaction:
                raise PaymentAlreadyMade(
                    f"Account {account.id} already has a successful payment"
                )

        transaction, created = PaymentTransaction.objects.get_or_create(
            gateway=PaymentTransaction.UZUM,
            transaction_id=trans_id,
            defaults={
                "account_id": str(account.id),
                "amount": Decimal(amount) / 100,
                "state": PaymentTransaction.CREATED,
                "extra_data": {"raw_params": data},
            },
        )

        if not created:
            if transaction.state == PaymentTransaction.SUCCESSFULLY:
                # Already paid - return error 10008
                raise PaymentAlreadyMade("Payment has already been made")
            elif transaction.state == PaymentTransaction.CANCELLED:
                # Transaction was cancelled - return error 10009
                raise TransactionCancelled("Transaction has been cancelled")

        extra_data = self.get_check_data(params, account) or {}
        response_data = {"account": {"value": str(account.id)}}
        response_data.update(extra_data)

        # Use transaction created_at for transTime
        trans_time = int(transaction.created_at.timestamp() * 1000)

        return {
            "serviceId": service_id,
            "transId": trans_id,
            "status": UzumStatus.CREATED,
            "transTime": trans_time,
            "data": response_data,
            "amount": amount,
        }

    def _handle_confirm(self, data):
        trans_id = data.get("transId")
        service_id = data.get("serviceId", self.service_id)

        try:
            transaction = PaymentTransaction.objects.get(
                gateway=PaymentTransaction.UZUM, transaction_id=trans_id
            )
        except PaymentTransaction.DoesNotExist:
            # Transaction not found
            # raise TransactionNotFound -> 10009 or 99999
            raise TransactionNotFound("Transaction not found")

        if transaction.state != PaymentTransaction.SUCCESSFULLY:
            transaction.mark_as_paid()
            self.successfully_payment(data, transaction)

        # Prepare data for response
        account = None
        if transaction.account_id:
            try:
                account = self.account_model._default_manager.get(
                    pk=transaction.account_id
                )
            except self.account_model.DoesNotExist:
                pass

        params = data.get("params", {})
        if not params and transaction.extra_data:
            params = transaction.extra_data.get("raw_params", {}).get("params", {})

        response_data = {}
        if account:
            response_data["account"] = {"value": str(account.id)}
            extra_data = self.get_check_data(params, account) or {}
            response_data.update(extra_data)

        # Use transaction updated_at for confirmTime (when it was confirmed)
        confirm_time = int(transaction.updated_at.timestamp() * 1000)
        # Use transaction created_at for transTime
        trans_time = int(transaction.created_at.timestamp() * 1000)

        return {
            "serviceId": service_id,
            "transId": trans_id,
            "status": UzumStatus.CONFIRMED,
            "confirmTime": confirm_time,
            "transTime": trans_time,
            "data": response_data,
            "amount": int(transaction.amount * 100),
        }

    def _handle_reverse(self, data):
        trans_id = data.get("transId")
        service_id = data.get("serviceId", self.service_id)

        try:
            transaction = PaymentTransaction.objects.get(
                gateway=PaymentTransaction.UZUM, transaction_id=trans_id
            )
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound("Transaction not found")

        # Check if transaction is already cancelled
        if transaction.state == PaymentTransaction.CANCELLED:
            raise TransactionCancelled("Transaction has already been cancelled")

        transaction.mark_as_cancelled()
        self.cancelled_payment(data, transaction)

        # Prepare data for response
        account = None
        if transaction.account_id:
            try:
                account = self.account_model._default_manager.get(
                    pk=transaction.account_id
                )
            except self.account_model.DoesNotExist:
                pass

        params = data.get("params", {})
        if not params and transaction.extra_data:
            params = transaction.extra_data.get("raw_params", {}).get("params", {})

        response_data = {}
        if account:
            response_data["account"] = {"value": str(account.id)}
            extra_data = self.get_check_data(params, account) or {}
            response_data.update(extra_data)

        return {
            "serviceId": service_id,
            "transId": trans_id,
            "status": UzumStatus.REVERSED,
            "reverseTime": int(datetime.now().timestamp() * 1000),
            "data": response_data,
            "amount": int(transaction.amount * 100),
        }

    def _handle_status(self, data):
        trans_id = data.get("transId")
        service_id = data.get("serviceId", self.service_id)

        try:
            transaction = PaymentTransaction.objects.get(
                gateway=PaymentTransaction.UZUM, transaction_id=trans_id
            )

            status = UzumStatus.CREATED
            confirm_time = None
            reverse_time = None

            # Set confirmTime if transaction was ever confirmed (performed_at is set)
            if transaction.performed_at:
                confirm_time = int(transaction.performed_at.timestamp() * 1000)

            if transaction.state == PaymentTransaction.SUCCESSFULLY:
                status = UzumStatus.CONFIRMED
            elif transaction.state == PaymentTransaction.CANCELLED:
                status = UzumStatus.REVERSED
                if transaction.cancelled_at:
                    reverse_time = int(transaction.cancelled_at.timestamp() * 1000)

            # Prepare data for response
            account = None
            if transaction.account_id:
                try:
                    account = self.account_model._default_manager.get(
                        pk=transaction.account_id
                    )
                except self.account_model.DoesNotExist:
                    pass

            params = data.get("params", {})
            if not params and transaction.extra_data:
                params = transaction.extra_data.get("raw_params", {}).get("params", {})

            response_data = {}
            if account:
                response_data["account"] = {"value": str(account.id)}
                extra_data = self.get_check_data(params, account) or {}
                response_data.update(extra_data)

            return {
                "serviceId": service_id,
                "transId": trans_id,
                "status": status,
                "transTime": int(transaction.created_at.timestamp() * 1000),
                "confirmTime": confirm_time,
                "reverseTime": reverse_time,
                "data": response_data,
                "amount": int(transaction.amount * 100),
            }
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound("Transaction not found")

    # Event hooks
    def successfully_payment(self, params, transaction):
        pass

    def cancelled_payment(self, params, transaction):
        pass

    def get_check_data(self, params, account):
        """
        Override this method to return extra data for 'check' action.

        Args:
            params: Request parameters
            account: Account object

        Returns:
            Dict containing extra fields to be merged into 'data' field of response.
            Example: { "fio": { "value": "Ivanov Ivan" } }
        """
        pass
