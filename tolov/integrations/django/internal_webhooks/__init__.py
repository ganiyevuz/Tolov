"""
Internal Django webhook handlers for Tolov.
"""
from .payme import PaymeWebhook
from .click import ClickWebhook
from .uzum import UzumWebhook
from .paynet import PaynetWebhook
from .octo import OctoWebhook
from .multicard import MulticardWebhook

__all__ = [
    "PaymeWebhook",
    "ClickWebhook",
    "UzumWebhook",
    "PaynetWebhook",
    "OctoWebhook",
    "MulticardWebhook",
]
