"""
FastAPI routes for Tolov.

Public webhook handlers that provide type hints and IDE support.
These classes inherit from internal handlers which contain the compiled business logic.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from .internal import (
    PaymeWebhookHandlerInternal,
    ClickWebhookHandlerInternal,
)
from .models import PaymentTransaction

router = APIRouter()
logger = logging.getLogger(__name__)


class PaymeWebhookHandler(PaymeWebhookHandlerInternal):
    """
    Base Payme webhook handler for FastAPI.

    This class handles webhook requests from the Payme payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.fastapi import PaymeWebhookHandler

    class CustomPaymeWebhookHandler(PaymeWebhookHandler):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")

            # Update your order status
            order = db.query(Order).filter(
                Order.id == transaction.account_id
            ).first()
            order.status = 'paid'
            db.commit()
    ```
    """

    def __init__(
        self,
        db: Session,
        payme_id: str,
        payme_key: str,
        account_model: Any,
        account_field: str = 'id',
        amount_field: str = 'amount',
        one_time_payment: bool = True
    ):
        """
        Initialize the Payme webhook handler.

        Args:
            db: Database session
            payme_id: Payme merchant ID
            payme_key: Payme merchant key
            account_model: Account model class
            account_field: Account field name
            amount_field: Amount field name
            one_time_payment: Whether to validate amount
        """
        super().__init__(
            db=db,
            payme_id=payme_id,
            payme_key=payme_key,
            account_model=account_model,
            account_field=account_field,
            amount_field=amount_field,
            one_time_payment=one_time_payment
        )

    async def handle_webhook(self, request: Request) -> Response:
        """
        Handle webhook request from Payme.

        Args:
            request: FastAPI request object

        Returns:
            Response object with JSON data
        """
        return await super().handle_webhook(request)

    # Event methods that can be overridden by subclasses

    def before_check_perform_transaction(
        self, params: Dict[str, Any], account: Any
    ) -> None:
        """
        Called before checking if a transaction can be performed.

        Args:
            params: Request parameters
            account: Account object
        """
        pass

    def transaction_already_exists(
        self, params: Dict[str, Any], transaction: PaymentTransaction
    ) -> None:
        """
        Called when a transaction already exists.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def transaction_created(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction,
        account: Any
    ) -> None:
        """
        Called when a transaction is created.

        Args:
            params: Request parameters
            transaction: Transaction object
            account: Account object
        """
        pass

    def successfully_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def check_transaction(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """
        Called when checking a transaction.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def cancelled_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def get_statement(
        self,
        params: Dict[str, Any],
        transactions: list
    ) -> None:
        """
        Called when getting a statement.

        Args:
            params: Request parameters
            transactions: List of transactions
        """
        pass


class ClickWebhookHandler(ClickWebhookHandlerInternal):
    """
    Base Click webhook handler for FastAPI.

    This class handles webhook requests from the Click payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from tolov.integrations.fastapi import ClickWebhookHandler

    class CustomClickWebhookHandler(ClickWebhookHandler):
        def successfully_payment(self, params, transaction):
            # Your custom logic here
            print(f"Payment successful: {transaction.transaction_id}")

            # Update your order status
            order = (db.query(Order)
                     .filter(Order.id == transaction.account_id)
                     .first())
            order.status = 'paid'
            db.commit()
    ```
    """

    def __init__(
        self,
        db: Session,
        service_id: str,
        secret_key: str,
        account_model: Any,
        commission_percent: float = 0.0,
        account_field: str = 'id',
        one_time_payment: bool = True
    ):
        """
        Initialize the Click webhook handler.

        Args:
            db: Database session
            service_id: Click service ID
            secret_key: Click secret key
            account_model: Account model class
            commission_percent: Commission percentage
            account_field: Field name to look up account by (default: 'id')
            one_time_payment: Whether to validate amount (default: True)
        """
        super().__init__(
            db=db,
            service_id=service_id,
            secret_key=secret_key,
            account_model=account_model,
            commission_percent=commission_percent,
            account_field=account_field,
            one_time_payment=one_time_payment
        )

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """
        Handle webhook request from Click.

        Args:
            request: FastAPI request object

        Returns:
            Response data
        """
        return await super().handle_webhook(request)

    # Event methods that can be overridden by subclasses

    def transaction_already_exists(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """
        Called when a transaction already exists.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def transaction_created(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction,
        account: Any
    ) -> None:
        """
        Called when a transaction is created.

        Args:
            params: Request parameters
            transaction: Transaction object
            account: Account object
        """
        pass

    def successfully_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass

    def cancelled_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        pass



