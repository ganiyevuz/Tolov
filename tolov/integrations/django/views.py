"""
Django views for Tolov.
"""
import logging

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .webhooks import PaymeWebhook, ClickWebhook, UzumWebhook, PaynetWebhook, OctoWebhook

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class BasePaymeWebhookView(PaymeWebhook):
    """
    Default Payme webhook view.

    This view handles webhook requests from the Payme payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.views import PaymeWebhookView

    class CustomPaymeWebhookView(PaymeWebhookView):
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
            params: Request parameters
            transaction: Transaction object
        """
        logger.info(f"Payme payment successful: {transaction.transaction_id}")

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        logger.info(f"Payme payment cancelled: {transaction.transaction_id}")

    def get_check_data(self, params, account):
        """
        Override this method to return extra data in check response.
        By default returns empty dict.
        """


@method_decorator(csrf_exempt, name='dispatch')
class BaseClickWebhookView(ClickWebhook):
    """
    Default Click webhook view.

    This view handles webhook requests from the Click payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.views import ClickWebhookView

    class CustomClickWebhookView(ClickWebhookView):
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
            params: Request parameters
            transaction: Transaction object
        """
        logger.info(f"Click payment successful: {transaction.transaction_id}")

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        logger.info(f"Click payment cancelled: {transaction.transaction_id}")



@method_decorator(csrf_exempt, name='dispatch')
class BaseUzumWebhookView(UzumWebhook):
    """
    Default Uzum webhook view.

    This view handles webhook requests from the Uzum payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.views import BaseUzumWebhookView

    class CustomUzumWebhookView(BaseUzumWebhookView):
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
        """
        logger.info(f"Uzum payment successful: {transaction.transaction_id}")

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.
        """
        logger.info(f"Uzum payment cancelled: {transaction.transaction_id}")

    def get_check_data(self, params, account):
        """
        Override this method to return extra data in check response.
        By default returns empty dict.
        """


@method_decorator(csrf_exempt, name='dispatch')
class BasePaynetWebhookView(PaynetWebhook):
    """
    Default Paynet webhook view.

    This view handles webhook requests from the Paynet payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.views import BasePaynetWebhookView

    class CustomPaynetWebhookView(BasePaynetWebhookView):
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
        """
        logger.info(f"Paynet payment successful: {transaction.transaction_id}")

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.
        """
        logger.info(f"Paynet payment cancelled: {transaction.transaction_id}")

    def get_check_data(self, params, account):
        """
        Override this method to return extra data in check response.
        By default returns empty dict.
        """


@method_decorator(csrf_exempt, name='dispatch')
class BaseOctoWebhookView(OctoWebhook):
    """
    Default Octo webhook view.

    This view handles callback notifications from the Octo payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.django.views import BaseOctoWebhookView

    class CustomOctoWebhookView(BaseOctoWebhookView):
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
        """
        logger.info(f"Octo payment successful: {transaction.transaction_id}")

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.
        """
        logger.info(f"Octo payment cancelled: {transaction.transaction_id}")
