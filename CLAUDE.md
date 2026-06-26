# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`tolov` is a published PyPI library: a unified payment SDK for Uzbekistan's providers — **Payme, Click, Uzum, Paynet, Octo** — exposing one consistent API across all of them, in both sync and async flavors, with drop-in webhook handlers for Django, FastAPI, and Flask. It is a *library*, not an application: there is no server to run, no settings module, and (currently) no test suite.

## Commands

Dependency management is **uv** (`uv.lock` is committed). Per the global rule, run `uv sync` after editing `pyproject.toml`.

```bash
uv sync                          # install/refresh the env from uv.lock
uv build                         # build sdist + wheel into dist/
uv publish                       # upload to PyPI (needs UV_PUBLISH_TOKEN)
make upload                      # = ./scripts/release.sh (clean → build → publish)

# Lint / format / type-check (dev deps, no make targets wired up)
uv run black tolov               # formatter, pinned black==22.3.0
uv run isort tolov               # import sorter (black profile)
uv run flake8 tolov              # max-line-length = 121
uv run mypy tolov
```

Releases are automated: pushing a GitHub **Release** triggers `.github/workflows/release.yaml`, which runs `scripts/release.sh`. There is no CI for lint/tests.

## Architecture

Three layers, plus framework integrations:

```
tolov/core/        shared abstractions used by every gateway
tolov/gateways/    one sub-package per provider (the sync implementation)
tolov/aio/         async variants of the gateways
tolov/integrations/{django,fastapi,flask}/   webhook handlers + persistence
tolov/factory.py   create_gateway("payme", **kwargs) string dispatch
```

### Core (`tolov/core/`)
- `base.py` — `BasePaymentGateway` (ABC: `create_payment`/`check_payment`/`cancel_payment`), `BaseWebhookHandler`, `BasePaymentProcessor` (Basic-Auth check).
- `http.py` — `HttpClient` / `AsyncHttpClient`, thin `httpx` wrappers over persistent (connection-pooling) clients. Both share one `_handle_response` because httpx's `Response` API is identical sync/async; both translate httpx errors into the exception hierarchy.
- `exceptions.py` — a tree under `PaymentException` (auth / transaction / account / amount / method / system). `exception_whitelist` lists the ones that must propagate unchanged.
- `utils.py` — `format_amount` (som → tiyin, ×100), `generate_hmac_signature`, `generate_basic_auth`, and `handle_exceptions` (see below).
- `constants.py` — `PaymentGateway` and `TransactionState` enums.

### Gateways (`tolov/gateways/<provider>/`)
Each provider package follows the same shape:
- **`client.py`** — the public, user-facing class (`PaymeGateway`, `ClickGateway`, …). Thin, heavily-docstringed wrapper.
- **`internal.py`** — the actual business logic. The header comments say this is intended to be compiled to `.so` (pyarmor obfuscation); that's the reason for the client/internal split.
- **`constants.py`** — endpoint URLs (test vs prod), provider error codes.
- Provider extras: Payme adds `cards.py` + `receipts.py`; Click adds `merchant.py`.

> The standard `uv build` ships `internal.py` as plain `.py`; obfuscation runs only via the separate `make obfuscate` (pyarmor) target against `./tolov`.

### Async (`tolov/aio/`)
Async classes **subclass the sync gateway and override only the methods that make HTTP calls**, marking them `async`. Pure-compute methods (e.g. `generate_pay_link`, `create_payment` for Payme) are inherited untouched. The key enabling pattern: sync request methods are split into a `_build_*_request(...) -> (data, headers)` helper plus the actual call, so the async override reuses `_build_*` and only swaps `self.http_client.post(...)` for `await`. `_setup_clients` is overridden to inject `AsyncHttpClient`. Import async via `from tolov.aio import PaymeGateway`.

### `@handle_exceptions` (in `core/utils.py`)
Wraps public gateway methods. It detects coroutine functions and returns the matching sync/async wrapper. Whitelisted `PaymentException` subclasses re-raise as-is; any other exception is logged and re-raised as `InternalServiceError`. Apply it to new public-facing gateway methods.

### Framework integrations (`tolov/integrations/`)
- **Django** — `PaymentTransaction` model (`db_table="payments"`, `unique_together=(gateway, transaction_id)`, integer `state` codes matching the Payme protocol: `-2,-1,0,1,2`). The app is registered as `tolov.integrations.django` in `INSTALLED_APPS`; config lives in a single `settings.TOLOV` dict keyed by provider (`PAYME`, `CLICK`, …). Webhook flow mirrors the gateway client/internal split: `internal_webhooks/<provider>.py` holds the protocol logic (CBVs subclassing Django `View`); `webhooks.py` and `views.py` expose the `Base<Provider>WebhookView` classes that users subclass to override lifecycle hooks (`successfully_payment`, `cancelled_payment`, `get_check_data`). Account lookups use `import_string` against `ACCOUNT_MODEL`.
- **FastAPI** — SQLAlchemy-based; `run_migrations(engine)` creates the transaction table. Config is passed to the handler constructor (not a global settings dict); handlers are wired into routes via `Depends(get_db)`.

## Conventions & gotchas

- **Money is in tiyin (1 som = 100 tiyin).** `format_amount` and `generate_pay_link` multiply by 100. Provider APIs disagree on the unit at their boundary (e.g. Uzum auto-converts som→tiyin in `create_payment`; Paynet's `create_payment` expects tiyin directly). When touching amounts, confirm the unit per provider against the README + that provider's `internal.py`.
- **Bump `__version__` and `pyproject.toml` together.** The version lives in two places (`tolov/__init__.py` `__version__` and `[project].version`); update both in the same change so they don't drift.
- **Python ≥ 3.9.** Use `typing.Dict/Optional/Union` rather than 3.10+ `X | Y` / built-in generics, to preserve compatibility.
- **Logging is `loguru`** throughout (`from loguru import logger`) — matches the global rule; never use stdlib `logging`.
- **Framework deps are optional extras.** `tolov/__init__.py` sets `HAS_DJANGO`/`HAS_FASTAPI`/`HAS_FLASK` by trying the import; integration code must not be imported at top level of the always-on path. New gateway code in `core`/`gateways` must not hard-depend on Django/FastAPI/Flask.
- **Adding a provider** means: a `gateways/<name>/` package (client + internal + constants), an `aio/_<name>.py` async subclass, a `PaymentGateway` enum entry, a `factory.create_gateway` branch, and integration webhook handlers + a model choice.
