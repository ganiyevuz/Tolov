"""
Django webhook handlers for Tolov.

Public webhook classes that provide type hints and IDE support.
These classes inherit from internal webhooks which contain the compiled business logic.
"""
from loguru import logger

from .internal_webhooks import (
    PaymeWebhook as PaymeWebhookInternal,
    ClickWebhook as ClickWebhookInternal,
    UzumWebhook as UzumWebhookInternal,
    PaynetWebhook as PaynetWebhookInternal,
    OctoWebhook as OctoWebhookInternal,
    MulticardWebhook as MulticardWebhookInternal,
)


class PaymeWebhook(PaymeWebhookInternal):
    """
    Base Payme webhook handler for Django.

    This class handles webhook requests from the Payme payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.webhooks import PaymeWebhook

    class CustomPaymeWebhook(PaymeWebhook):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")

            # Update your order status
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    # Event methods that can be overridden by subclasses

    def before_check_perform_transaction(self, params, account):
        """
        Called before checking if a transaction can be performed.

        Args:
            params: Request parameters
            account: Account object
        """
        pass

    def transaction_already_exists(self, params, transaction):
        """
        Called when a transaction already exists.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def transaction_created(self, params, transaction, account):
        """
        Called when a transaction is created.

        Args:
            params: Request parameters
            transaction: Transaction object
            account: Account object
        """
        pass

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def check_transaction(self, params, transaction):
        """
        Called when checking a transaction.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def get_statement(self, params, transactions):
        """
        Called when getting a statement.

        Args:
            params: Request parameters
            transactions: List of transactions
        """
        pass

    def get_check_data(self, params, account):
        """
        Override this method to return additional data for CheckPerformTransaction.

        Args:
            params: Request parameters
            account: Account object

        Returns:
            Dict containing additional fields to merge into response.
            Example:
            {
                "additional": {"key": "value"}, # for example {"first_name": "Anvarbek", "balance": 1000000}
                "detail": {
                    "receipt_type": 0,
                    "shipping": {"title": "Yetkazib berish", "price": 10000},
                    "items": [
                        {
                            "discount": 0,
                            "title": "Mahsulot nomi",
                            "price": 500000,
                            "count": 1,
                            "code": "00001",
                            "units": 1,
                            "vat_percent": 0,
                            "package_code": "123456"
                        }
                    ]
                }
            }
        """
        pass


class ClickWebhook(ClickWebhookInternal):
    """
    Base Click webhook handler for Django.

    This class handles webhook requests from the Click payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.webhooks import ClickWebhook

    class CustomClickWebhook(ClickWebhook):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")

            # Update your order status
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    # Event methods that can be overridden by subclasses

    def before_check_perform_transaction(self, params, account):
        """
        Called before checking if a transaction can be performed.

        Args:
            params: Request parameters
            account: Account object
        """
        pass

    def transaction_already_exists(self, params, transaction):
        """
        Called when a transaction already exists.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def transaction_created(self, params, transaction, account):
        """
        Called when a transaction is created.

        Args:
            params: Request parameters
            transaction: Transaction object
            account: Account object
        """
        pass

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass


class UzumWebhook(UzumWebhookInternal):
    """
    Base Uzum webhook handler for Django.

    Example:
    ```python
    from tolov.integrations.django.webhooks import UzumWebhook

    class CustomUzumWebhook(UzumWebhook):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")

        def get_check_data(self, params, account):
            return {
                "fio": {
                    "value": f"{account.first_name} {account.last_name}"
                }
            }
    ```
    """

    def successfully_payment(self, params, transaction):
        pass

    def cancelled_payment(self, params, transaction):
        pass

    def get_check_data(self, params, account):
        """
        Override this method to return extra data in check response.
        By default returns empty dict.
        """
        pass


class PaynetWebhook(PaynetWebhookInternal):
    """
    Base Paynet webhook handler for Django.

    This class handles webhook requests from the Paynet payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.webhooks import PaynetWebhook

    class CustomPaynetWebhook(PaynetWebhook):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def get_check_data(self, params, account):
        """
        Override this method to return additional data for GetInformation.

        Args:
            params: Request parameters
            account: Account object

        Returns:
            Dict containing additional fields to merge into response.
            Example:
            {
                "fields": {"first_name": "Vali"},
                "balance": 10000
            }
        """
        pass


class OctoWebhook(OctoWebhookInternal):
    """
    Base Octo webhook handler for Django.

    This class handles callback notifications from the Octo payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.webhooks import OctoWebhook

    class CustomOctoWebhook(OctoWebhook):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")

            # Update your order status
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Callback data from Octo
            transaction: PaymentTransaction object
        """
        pass

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled or failed.

        Args:
            params: Callback data from Octo
            transaction: PaymentTransaction object
        """
        pass


class MulticardWebhook(MulticardWebhookInternal):
    """
    Base Multicard webhook handler for Django (success callback).

    Override ``successfully_payment`` to update your order when Multicard
    confirms a payment.

    Example:
    ```python
    from tolov.integrations.django.webhooks import MulticardWebhook

    class CustomMulticardWebhook(MulticardWebhook):
        def successfully_payment(self, params, transaction):
            order = Order.objects.get(id=transaction.account_id)
            order.status = "paid"
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Callback data from Multicard
            transaction: PaymentTransaction object
        """
        pass
