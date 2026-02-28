"""
Django app configuration for Tolov.
"""
from django.apps import AppConfig


class TolovConfig(AppConfig):
    """
    Django app configuration for Tolov.
    """
    name = 'tolov.integrations.django'
    verbose_name = 'Tolov'

    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        """
        Initialize the app.
        """
        try:
            import tolov.integrations.django.signals  # noqa
        except ImportError:
            pass
