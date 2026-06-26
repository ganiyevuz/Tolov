"""Shared pytest configuration and fixtures for the Multicard test suite.

Sandbox credentials below are the PUBLIC test credentials documented at
https://docs.multicard.uz — safe to hardcode for sandbox tests.
"""
import socket

import pytest

# --- Public Multicard sandbox credentials (from the docs) ---
APPLICATION_ID = "rhmt_test"
SECRET = "Pw18axeBFo8V7NamKHXX"
STORE_ID = 105  # "Jett.uz" — an active sandbox store that accepts invoices
BASE_DEV = "https://dev-mesh.multicard.uz"
TEST_CARD = {"pan": "8600533364098829", "expire": "2806", "otp": "112233"}

# A token response with a far-future expiry, for mocked (offline) tests.
AUTH_OK = {"token": "test-jwt-token", "role": "dev", "expiry": "2099-01-01 00:00:00"}


# --- Django setup (needed to import the Django webhook + model) ---
import django  # noqa: E402
from django.conf import settings  # noqa: E402

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "tolov.integrations.django",
        ],
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        USE_TZ=True,
        TOLOV={"MULTICARD": {"SECRET": "testsecret"}},
    )
    django.setup()


@pytest.fixture(scope="session")
def django_migrated():
    """Create the PaymentTransaction table once for the test session."""
    from django.core.management import call_command

    call_command("migrate", verbosity=0)
    return True


def _network_up(host="dev-mesh.multicard.uz", port=443, timeout=3):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def live():
    """Skip live tests when the sandbox is unreachable."""
    if not _network_up():
        pytest.skip("Multicard sandbox not reachable")
    return True
