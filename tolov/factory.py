from tolov.core.base import BasePaymentGateway
from tolov.core.constants import PaymentGateway

from tolov.gateways.payme.client import PaymeGateway
from tolov.gateways.click.client import ClickGateway
from tolov.gateways.uzum.client import UzumGateway
from tolov.gateways.paynet.client import PaynetGateway
from tolov.gateways.multicard.client import MulticardGateway


def create_gateway(gateway_type: str, **kwargs) -> BasePaymentGateway:
    """
    Create a payment gateway instance.

    Args:
        gateway_type: Type of gateway ('payme', 'click', 'uzum', or 'paynet')
        **kwargs: Gateway-specific configuration

    Returns:
        Payment gateway instance

    Raises:
        ValueError: If the gateway type is not supported
        ImportError: If the required gateway module is not available
    """
    if gateway_type.lower() == PaymentGateway.PAYME.value:
        return PaymeGateway(**kwargs)
    if gateway_type.lower() == PaymentGateway.CLICK.value:
        return ClickGateway(**kwargs)
    if gateway_type.lower() == PaymentGateway.UZUM.value:
        return UzumGateway(**kwargs)
    if gateway_type.lower() == PaymentGateway.PAYNET.value:
        return PaynetGateway(**kwargs)
    if gateway_type.lower() == PaymentGateway.MULTICARD.value:
        return MulticardGateway(**kwargs)

    raise ValueError(f"Unsupported gateway type: {gateway_type}")
