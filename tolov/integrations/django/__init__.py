"""
Django integration for Tolov.
"""

# Check if Django dependencies are available
try:
    from tolov.core.dependencies import check_dependencies
    check_dependencies('django', raise_error=False)
except ImportError:
    pass  # dependencies module not available yet during build

# Register the app configuration
default_app_config = 'tolov.integrations.django.apps.TolovConfig'

# This is used to prevent Django from creating new migrations
# when the model changes. Instead, users should use the provided
# migration or create their own if needed.
TOLOV_PREVENT_MIGRATIONS = True


def get_payment_transaction_model():
    """
    Get the PaymentTransaction model lazily to avoid AppRegistryNotReady errors.
    
    Usage:
        PaymentTransaction = get_payment_transaction_model()
    """
    from tolov.integrations.django.models import PaymentTransaction
    return PaymentTransaction


__all__ = ['get_payment_transaction_model']

