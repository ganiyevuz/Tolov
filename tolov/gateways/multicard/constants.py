"""Multicard payment gateway constants."""


class MulticardNetworks:
    """Multicard API base URLs."""

    TEST_NET = "https://dev-mesh.multicard.uz"
    PROD_NET = "https://mesh.multicard.uz"


class MulticardEndpoints:
    """Multicard API endpoint paths (relative to the base URL)."""

    AUTH = "/auth"
    INVOICE = "/payment/invoice"  # POST create; GET/DELETE /{uuid}
    PAYMENT = "/payment"  # GET/PUT/DELETE /{uuid}
    CARD = "/payment/card"  # GET/DELETE /{card_token}
    CARD_BIND = "/payment/card/bind"  # POST bind; GET /{session_id} check state
    CARD_CHECK_PINFL = "/payment/card/check-pinfl"  # POST


class MulticardStatus:
    """PaymentStatusEnum values."""

    DRAFT = "draft"
    PROGRESS = "progress"
    BILLING = "billing"
    SUCCESS = "success"
    ERROR = "error"
    REVERT = "revert"
    HOLD = "hold"


class MulticardErrors:
    """Multicard error.code values referenced in handling."""

    NOT_FOUND = "ERROR_NOT_FOUND"
    CARD_NOT_FOUND = "ERROR_CARD_NOT_FOUND"
    FIELDS = "ERROR_FIELDS"
    DEBIT_UNKNOWN = "ERROR_DEBIT_UNKNOWN"
    CALLBACK_TIMEOUT = "ERROR_CALLBACK_TIMEOUT"
    UNKNOWN = "ERROR_UNKNOWN"


# Multicard status -> PaymentTransaction integer state (-2..2)
STATUS_TO_STATE = {
    MulticardStatus.DRAFT: 0,  # CREATED
    MulticardStatus.PROGRESS: 1,  # INITIATING
    MulticardStatus.BILLING: 1,
    MulticardStatus.HOLD: 1,
    MulticardStatus.SUCCESS: 2,  # SUCCESSFULLY
    MulticardStatus.ERROR: -1,  # CANCELLED_DURING_INIT
    MulticardStatus.REVERT: -2,  # CANCELLED
}
