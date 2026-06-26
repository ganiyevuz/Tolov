"""Mocked tests for the Multicard token-managed session."""
import pytest
import respx
from httpx import Response

from conftest import AUTH_OK, BASE_DEV
from tolov.gateways.multicard.session import MulticardSession
from tolov.core.exceptions import TransactionNotFound, ExternalServiceError


def _session():
    return MulticardSession(application_id="a", secret="s", is_test_mode=True)


@respx.mock
def test_auth_parsed_directly_not_via_envelope():
    """Regression: POST /auth returns {token,role,expiry} with NO {success,data}."""
    auth = respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))
    ep = respx.get(f"{BASE_DEV}/payment/application").mock(
        return_value=Response(200, json={"success": True, "data": {"id": 4}})
    )
    assert _session().get("/payment/application") == {"id": 4}
    assert auth.called
    assert ep.calls.last.request.headers["authorization"] == "Bearer test-jwt-token"


@respx.mock
def test_token_is_cached_across_requests():
    auth = respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))
    respx.get(f"{BASE_DEV}/x").mock(
        return_value=Response(200, json={"success": True, "data": 1})
    )
    s = _session()
    s.get("/x")
    s.get("/x")
    s.get("/x")
    assert auth.call_count == 1


@respx.mock
def test_token_refetched_when_expired():
    past = {"token": "t", "role": "dev", "expiry": "2000-01-01 00:00:00"}
    auth = respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=past))
    respx.get(f"{BASE_DEV}/x").mock(
        return_value=Response(200, json={"success": True, "data": 1})
    )
    s = _session()
    s.get("/x")
    s.get("/x")
    assert auth.call_count == 2


@respx.mock
def test_envelope_is_unwrapped():
    respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))
    respx.get(f"{BASE_DEV}/x").mock(
        return_value=Response(200, json={"success": True, "data": {"k": "v"}})
    )
    assert _session().get("/x") == {"k": "v"}


@respx.mock
def test_error_not_found_mapped_to_exception():
    respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))
    respx.get(f"{BASE_DEV}/x").mock(
        return_value=Response(
            400,
            json={"success": False, "error": {"code": "ERROR_NOT_FOUND", "details": "no"}},
        )
    )
    with pytest.raises(TransactionNotFound):
        _session().get("/x")


@respx.mock
def test_error_fields_is_generic_external_error():
    respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))
    respx.get(f"{BASE_DEV}/x").mock(
        return_value=Response(
            400,
            json={"success": False, "error": {"code": "ERROR_FIELDS", "details": "bad"}},
        )
    )
    with pytest.raises(ExternalServiceError) as exc_info:
        _session().get("/x")
    assert exc_info.value.code == "ERROR_FIELDS"


@respx.mock
def test_401_triggers_token_refresh_and_retry():
    auth = respx.post(f"{BASE_DEV}/auth").mock(return_value=Response(200, json=AUTH_OK))
    ep = respx.get(f"{BASE_DEV}/x").mock(
        side_effect=[
            Response(401, json={"success": False, "error": {"code": "ERROR_AUTH"}}),
            Response(200, json={"success": True, "data": "ok"}),
        ]
    )
    assert _session().get("/x") == "ok"
    assert auth.call_count == 2  # initial fetch + refresh after 401
    assert ep.call_count == 2
