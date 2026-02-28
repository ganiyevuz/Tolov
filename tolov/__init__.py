"""
Tolov - Unified payment library for Uzbekistan payment systems.

This library provides a unified interface for working with Payme, Click, and Uzum
payment systems in Uzbekistan. It supports Django, Flask, and FastAPI.
"""

__version__ = '1.0.0'

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

try:
    import flask  # noqa: F401
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# Import core components
from tolov.core.base import BasePaymentGateway  # noqa: E402
from tolov.gateways.payme.client import PaymeGateway  # noqa: E402
from tolov.gateways.click.client import ClickGateway  # noqa: E402
from tolov.gateways.uzum.client import UzumGateway  # noqa: E402
from tolov.gateways.octo.client import OctoGateway  # noqa: E402
from tolov.core.constants import PaymentGateway  # noqa: E402
from tolov.factory import create_gateway  # noqa: E402

# Import dependency checker for users who need it
from tolov.core.dependencies import (  # noqa: E402
    check_dependencies,
    require_framework,
    get_missing_dependencies,
    DependencyError
)

__all__ = [
    # Version
    '__version__',
    
    # Framework availability flags
    'HAS_DJANGO',
    'HAS_FASTAPI',
    'HAS_FLASK',
    
    # Core classes
    'BasePaymentGateway',
    'PaymeGateway',
    'ClickGateway',
    'UzumGateway',
    'OctoGateway',

    'PaymentGateway',
    
    # Factory
    'create_gateway',
    
    # Dependency management
    'check_dependencies',
    'require_framework',
    'get_missing_dependencies',
    'DependencyError',
]

