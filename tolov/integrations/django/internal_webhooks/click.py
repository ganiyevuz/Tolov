"""
Click internal webhook handler.
"""
import hashlib
import hmac
from loguru import logger
from django.conf import settings
from django.db.transaction import atomic
from django.http import JsonResponse
from django.utils.module_loading import import_string
from django.views import View

from tolov.core.exceptions import PermissionDenied, InvalidAmount, AccountNotFound
from tolov.integrations.django.models import PaymentTransaction


class ClickWebhook(View):
    """
    Base Click webhook handler for Django.

    This class handles webhook requests from the Click payment system.
    You can extend this class and override the event methods to customize
    the behavior.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        click_settings = settings.TOLOV.get("CLICK", {})

        account_model_path = click_settings.get("ACCOUNT_MODEL")
        try:
            self.account_model = import_string(account_model_path)
        except ImportError:
            logger.error(
                "Could not import %s. Check TOLOV.CLICK.ACCOUNT_MODEL setting.",
                account_model_path,
            )
            # Raise if critical or allow to continue if not strictly needed immediately
            if account_model_path:
                raise ImportError(f"Import error: {account_model_path}") from None

        self.service_id = click_settings.get("SERVICE_ID", "")
        self.secret_key = click_settings.get("SECRET_KEY", "")
        self.commission_percent = click_settings.get("COMMISSION_PERCENT", 0.0)
        self.account_field = click_settings.get("ACCOUNT_FIELD", "id")
        self.one_time_payment = click_settings.get("ONE_TIME_PAYMENT", True)

    def post(self, request, **_):
        """
        Handle POST requests from Click.
        """
        try:
            # Get parameters from request
            params = request.POST.dict()

            # Check authorization
            self._check_auth(params)

            # Extract parameters
            click_trans_id = params.get("click_trans_id")
            merchant_trans_id = params.get("merchant_trans_id")
            amount = float(params.get("amount", 0))
            action = int(params.get("action", -1))
            error = int(params.get("error", 0))

            # Find account
            try:
                account = self._find_account(merchant_trans_id)
            except AccountNotFound:
                logger.error("Account not found: %s", merchant_trans_id)
                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "error": -5,
                        "error_note": "User not found",
                    },
                    status=200,
                )

            self.before_check_perform_transaction(params, account)

            # Check if transaction already performed for this account
            existing_transaction = self._check_perform_transaction(account, params)
            if existing_transaction:
                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": existing_transaction.account_id,
                        "merchant_prepare_id": existing_transaction.id,
                        "error": 0,
                        "error_note": "Success",
                    }
                )

            # Validate amount
            try:
                # Get amount from account and validate
                # Assuming 'amount' is the field for price on the account model, or should be configured?
                # The original code used getattr(account, 'amount', 0).
                # But typically this should be configurable. For now, matching original logic.
                account_amount = float(getattr(account, "amount", 0))
                self._validate_amount(amount, account_amount)
            except InvalidAmount as e:
                logger.error("Invalid amount: %s", e)
                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "error": -2,
                        "error_note": str(e),
                    },
                    status=200,
                )

            # Check if transaction already exists
            try:
                transaction = PaymentTransaction._default_manager.get(
                    gateway=PaymentTransaction.CLICK, transaction_id=click_trans_id
                )

                # If transaction is already completed, return success
                if transaction.state == PaymentTransaction.SUCCESSFULLY:
                    self.transaction_already_exists(params, transaction)
                    return JsonResponse(
                        {
                            "click_trans_id": click_trans_id,
                            "merchant_trans_id": merchant_trans_id,
                            "merchant_prepare_id": transaction.id,
                            "error": 0,
                            "error_note": "Success",
                        }
                    )

                # If transaction is cancelled, return error
                if transaction.state == PaymentTransaction.CANCELLED:
                    return JsonResponse(
                        {
                            "click_trans_id": click_trans_id,
                            "merchant_trans_id": merchant_trans_id,
                            "merchant_prepare_id": transaction.id,
                            "error": -9,
                            "error_note": "Transaction cancelled",
                        }
                    )
            except PaymentTransaction.DoesNotExist:
                # Transaction doesn't exist, continue with the flow
                pass

            # Handle different actions
            if action == 0:  # Prepare
                transaction = PaymentTransaction.create_transaction(
                    gateway=PaymentTransaction.CLICK,
                    transaction_id=click_trans_id,
                    account_id=str(account.id),
                    amount=amount,
                    extra_data={
                        "raw_params": params,
                        "merchant_trans_id": merchant_trans_id,
                    },
                )

                transaction.state = PaymentTransaction.INITIATING
                transaction.save()
                self.transaction_created(params, transaction, account)

                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "merchant_prepare_id": transaction.id,
                        "error": 0,
                        "error_note": "Success",
                    }
                )

            # Complete action
            if action == 1:
                is_successful = error >= 0

                # Lock the row so concurrent provider retries serialize here and
                # the success/cancel hook fires exactly once.
                with atomic():
                    transaction = (
                        PaymentTransaction._default_manager.select_for_update()
                        .filter(
                            gateway=PaymentTransaction.CLICK,
                            transaction_id=click_trans_id,
                        )
                        .first()
                    )

                    if transaction is None:
                        # Complete without a prior Prepare — create, then re-lock.
                        PaymentTransaction.create_transaction(
                            gateway=PaymentTransaction.CLICK,
                            transaction_id=click_trans_id,
                            account_id=str(account.id),
                            amount=amount,
                            extra_data={
                                "raw_params": params,
                                "merchant_trans_id": merchant_trans_id,
                            },
                        )
                        transaction = (
                            PaymentTransaction._default_manager.select_for_update().get(
                                gateway=PaymentTransaction.CLICK,
                                transaction_id=click_trans_id,
                            )
                        )

                    if is_successful:
                        if transaction.state != PaymentTransaction.SUCCESSFULLY:
                            transaction.mark_as_paid()
                            self.successfully_payment(params, transaction)
                    elif transaction.state not in (
                        PaymentTransaction.CANCELLED,
                        PaymentTransaction.CANCELLED_DURING_INIT,
                    ):
                        transaction.mark_as_cancelled(reason=f"Error code: {error}")
                        self.cancelled_payment(params, transaction)

                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "merchant_prepare_id": transaction.id,
                        "error": 0,
                        "error_note": "Success",
                    }
                )

            # Handle unsupported action
            logger.error("Unsupported action: %s", action)
            return JsonResponse(
                {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "error": -3,
                    "error_note": "Action not found",
                },
                status=200,
            )

        except PermissionDenied as e:
            logger.error(f"Permission denied: {e}")
            return JsonResponse(
                {"error": -1, "error_note": "SIGN CHECK FAILED!"}, status=200
            )

        except Exception as e:
            logger.exception("Unexpected error in Click webhook: %s", e)
            return JsonResponse(
                {"error": -7, "error_note": "Internal error"}, status=200
            )

    def _check_auth(self, params):
        if not self.service_id or not self.secret_key:
            raise PermissionDenied(
                "Missing required settings: service_id or secret_key"
            )

        if str(params.get("service_id")) != self.service_id:
            raise PermissionDenied("Invalid service ID")

        sign_string = params.get("sign_string")
        sign_time = params.get("sign_time")

        if not sign_string or not sign_time:
            raise PermissionDenied("Missing signature parameters")

        text_parts = [
            str(params.get("click_trans_id") or ""),
            str(params.get("service_id") or ""),
            str(self.secret_key or ""),
            str(params.get("merchant_trans_id") or ""),
            str(params.get("merchant_prepare_id") or ""),
            str(params.get("amount") or ""),
            str(params.get("action") or ""),
            str(sign_time),
        ]

        calculated_hash = hashlib.md5("".join(text_parts).encode("utf-8")).hexdigest()

        # Constant-time compare: the secret_key is folded into the signed
        # string, so a short-circuiting ``!=`` leaks it to a timing oracle.
        if not hmac.compare_digest(
            calculated_hash.encode("utf-8"), str(sign_string).encode("utf-8")
        ):
            raise PermissionDenied("Invalid signature")

    def _find_account(self, merchant_trans_id):
        try:
            if self.account_field == "id":
                if isinstance(merchant_trans_id, str) and merchant_trans_id.isdigit():
                    merchant_trans_id = int(merchant_trans_id)

            lookup_kwargs = {self.account_field: merchant_trans_id}
            account = self.account_model._default_manager.get(**lookup_kwargs)
            return account
        except (self.account_model.DoesNotExist, ValueError):
            raise AccountNotFound(
                f"Account with {self.account_field}={merchant_trans_id} not found"
            ) from None

    def _check_perform_transaction(self, account, params):
        if self.one_time_payment:
            try:
                transaction = PaymentTransaction._default_manager.get(
                    gateway=PaymentTransaction.CLICK,
                    account_id=account.id,
                    state=PaymentTransaction.SUCCESSFULLY,
                )
                return transaction
            except PaymentTransaction.DoesNotExist:
                return None
        return None

    def _validate_amount(self, received_amount, expected_amount):
        if self.one_time_payment:
            if self.commission_percent > 0:
                expected_amount = expected_amount * (1 + self.commission_percent / 100)
                expected_amount = round(expected_amount, 2)

            if abs(received_amount - expected_amount) > 0.01:
                raise InvalidAmount(
                    f"Incorrect amount. Expected: {expected_amount}, received: {received_amount}"
                )
        else:
            if received_amount <= 0:
                raise InvalidAmount("Amount must be positive")

    # Event hooks
    def before_check_perform_transaction(self, params, account):
        pass

    def transaction_already_exists(self, params, transaction):
        pass

    def transaction_created(self, params, transaction, account):
        pass

    def successfully_payment(self, params, transaction):
        pass

    def cancelled_payment(self, params, transaction):
        pass
