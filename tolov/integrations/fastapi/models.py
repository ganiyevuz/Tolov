"""
FastAPI models for Tolov.
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PaymentTransaction(Base):
    """
    Payment transaction model for storing payment information.
    """

    __tablename__ = "payments"

    # Payment gateway choices
    PAYME = "payme"
    CLICK = "click"
    MULTICARD = "multicard"

    # Transaction states
    CREATED = 0
    INITIATING = 1
    SUCCESSFULLY = 2
    CANCELLED = -2
    CANCELLED_DURING_INIT = -1

    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(String(10), index=True)  # 'payme' or 'click'
    transaction_id = Column(String(255), index=True)
    account_id = Column(String(255), index=True)
    amount = Column(Float)
    state = Column(Integer, default=CREATED, index=True)
    reason = Column(Integer, nullable=True)  # Reason for cancellation
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )
    performed_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True, index=True)

    @classmethod
    def create_transaction(
        cls,
        db,
        gateway: str,
        transaction_id: str,
        account_id: str,
        amount: float,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> "PaymentTransaction":
        """
        Create a new transaction or get an existing one.

        Args:
            db: Database session
            gateway: Payment gateway (payme or click)
            transaction_id: Transaction ID from the payment system
            account_id: Account or order ID
            amount: Payment amount
            extra_data: Additional data for the transaction

        Returns:
            PaymentTransaction instance
        """
        # Check if transaction already exists
        transaction = (
            db.query(cls)
            .filter(cls.gateway == gateway, cls.transaction_id == transaction_id)
            .first()
        )

        if transaction:
            return transaction

        # Create new transaction
        transaction = cls(
            gateway=gateway,
            transaction_id=transaction_id,
            account_id=str(account_id),
            amount=amount,
            state=cls.CREATED,
            extra_data=extra_data or {},
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return transaction

    def mark_as_paid(self, db) -> "PaymentTransaction":
        """
        Mark the transaction as paid.

        Args:
            db: Database session

        Returns:
            PaymentTransaction instance
        """
        if self.state != self.SUCCESSFULLY:
            self.state = self.SUCCESSFULLY
            self.performed_at = datetime.utcnow()

            db.commit()
            db.refresh(self)

        return self

    def mark_as_cancelled(
        self, db, reason: Optional[str] = None
    ) -> "PaymentTransaction":
        """
        Mark the transaction as cancelled.

        Args:
            db: Database session
            reason: Reason for cancellation

        Returns:
            PaymentTransaction instance
        """
        reason_code = self._resolve_cancel_reason(reason)
        self._apply_cancel(reason_code)

        db.commit()
        db.refresh(self)

        return self

    # ------------------------------------------------------------------
    # Async variants (SQLAlchemy AsyncSession)
    #
    # Share the pure-compute state logic with the sync methods; only the
    # session I/O (query/commit/refresh) becomes ``await``. Used by the async
    # webhook handlers in ``aio.py``.
    # ------------------------------------------------------------------

    def _resolve_cancel_reason(self, reason):
        """Normalize a cancel reason into an int code (pure, no I/O)."""
        if reason is None:
            return 5  # REASON_FUND_RETURNED
        if isinstance(reason, str) and reason.isdigit():
            return int(reason)
        return reason

    def _apply_cancel(self, reason_code) -> None:
        """Apply the cancel state transition in memory (pure, no I/O)."""
        if self.state not in [self.CANCELLED, self.CANCELLED_DURING_INIT]:
            if self.state == self.INITIATING or reason_code == 3:
                self.state = self.CANCELLED_DURING_INIT
            else:
                self.state = self.CANCELLED
            self.cancelled_at = datetime.utcnow()

        self.reason = reason_code
        extra_data = self.extra_data or {}
        extra_data["cancel_reason"] = reason_code
        self.extra_data = extra_data

    @classmethod
    async def acreate_transaction(
        cls,
        db,
        gateway: str,
        transaction_id: str,
        account_id: str,
        amount: float,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> "PaymentTransaction":
        """Async get-or-create (see :meth:`create_transaction`)."""
        from sqlalchemy import select

        transaction = (
            await db.execute(
                select(cls).where(
                    cls.gateway == gateway, cls.transaction_id == transaction_id
                )
            )
        ).scalar_one_or_none()

        if transaction:
            return transaction

        transaction = cls(
            gateway=gateway,
            transaction_id=transaction_id,
            account_id=str(account_id),
            amount=amount,
            state=cls.CREATED,
            extra_data=extra_data or {},
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        return transaction

    async def amark_as_paid(self, db) -> "PaymentTransaction":
        """Async :meth:`mark_as_paid` — self-gated on ``!= SUCCESSFULLY``."""
        if self.state != self.SUCCESSFULLY:
            self.state = self.SUCCESSFULLY
            self.performed_at = datetime.utcnow()

            await db.commit()
            await db.refresh(self)

        return self

    async def amark_as_cancelled(
        self, db, reason: Optional[str] = None
    ) -> "PaymentTransaction":
        """Async :meth:`mark_as_cancelled`."""
        reason_code = self._resolve_cancel_reason(reason)
        self._apply_cancel(reason_code)

        await db.commit()
        await db.refresh(self)

        return self


def run_migrations(engine: Any) -> None:
    """
    Run database migrations for Tolov FastAPI integration.

    This function creates all necessary tables in the database for the
    Tolov payment system. Call this function when setting up your FastAPI
    application to ensure all required database tables are created.

    Example:
        ```python
        from sqlalchemy import create_engine
        from tolov.integrations.fastapi.models import run_migrations

        engine = create_engine("sqlite:///./payments.db")
        run_migrations(engine)
        ```

    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(bind=engine)


async def run_migrations_async(engine: Any) -> None:
    """
    Async variant of :func:`run_migrations` for a SQLAlchemy ``AsyncEngine``.

    Example:
        ```python
        from sqlalchemy.ext.asyncio import create_async_engine
        from tolov.integrations.fastapi.models import run_migrations_async

        engine = create_async_engine("sqlite+aiosqlite:///./payments.db")
        await run_migrations_async(engine)
        ```

    Args:
        engine: SQLAlchemy AsyncEngine instance
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
