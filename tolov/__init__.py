"""
Tolov - Unified payment library for Uzbekistan payment systems.

This library provides a unified interface for working with Payme, Click, Uzum,
Paynet, Octo, and Multicard payment systems in Uzbekistan. It supports Django
and FastAPI.
"""

__version__ = "2.2.0"

# Check framework availability
try:
    import django  # noqa: F401

    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False

try:
    import fastapi  # noqa: F401

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Import core components
from tolov.core.base import BasePaymentGateway  # noqa: E402
from tolov.gateways.payme.client import PaymeGateway  # noqa: E402
from tolov.gateways.click.client import ClickGateway  # noqa: E402
from tolov.gateways.uzum.client import UzumGateway  # noqa: E402
from tolov.gateways.octo.client import OctoGateway  # noqa: E402
from tolov.gateways.multicard.client import MulticardGateway  # noqa: E402
from tolov.core.constants import PaymentGateway  # noqa: E402
from tolov.factory import create_gateway  # noqa: E402

# Import dependency checker for users who need it
from tolov.core.dependencies import (  # noqa: E402
    check_dependencies,
    require_framework,
    get_missing_dependencies,
    DependencyError,
)

__all__ = [
    # Version
    "__version__",
    # Framework availability flags
    "HAS_DJANGO",
    "HAS_FASTAPI",
    # Core classes
    "BasePaymentGateway",
    "PaymeGateway",
    "ClickGateway",
    "UzumGateway",
    "OctoGateway",
    "MulticardGateway",
    "PaymentGateway",
    # Factory
    "create_gateway",
    # Dependency management
    "check_dependencies",
    "require_framework",
    "get_missing_dependencies",
    "DependencyError",
]
