"""
Internal Django webhook handlers for Tolov.
"""
from .payme import PaymeWebhook
from .click import ClickWebhook
from .uzum import UzumWebhook
from .paynet import PaynetWebhook
from .octo import OctoWebhook

__all__ = [
    'PaymeWebhook',
    'ClickWebhook',
    'UzumWebhook',
    'PaynetWebhook',
    'OctoWebhook',
]
