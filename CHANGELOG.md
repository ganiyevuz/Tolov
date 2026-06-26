# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-06-26

### Added

- **Multicard** payment provider — full sync (`tolov.MulticardGateway`) and async
  (`tolov.aio.MulticardGateway`) support, implementing the unified
  `BasePaymentGateway` interface (`create_payment` → checkout URL, `check_payment`,
  `cancel_payment`) plus namespaced sub-clients:
  - `invoices` — create / get / delete (hosted payment page)
  - `payments` — token payments (with split), app payments (payme/click/uzum/…),
    OTP confirmation, full and partial refunds, fiscal links, and lookup
  - `cards` — form-based binding, binding-state check, info by token, PINFL
    ownership check, and token revocation
  - `holds` — create / confirm / debit (partial allowed) / cancel / info
  - `payouts` — create (by card number or token) / confirm / info
  - `reports` — application & wallet info, recipient requisites, payment
    registry, and payout history
- Token-managed `MulticardSession` / `AsyncMulticardSession` with automatic JWT
  fetch, caching, expiry refresh, and `Authorization: Bearer` injection.
- Django (`BaseMulticardWebhookView`) and FastAPI (`MulticardWebhookHandler`)
  success-callback handlers. `multicard` added to the `PaymentTransaction` model
  (migration `0002`), the `PaymentGateway` enum, and the `create_gateway` factory.
- Test suite under `tests/`: `respx`-mocked unit tests covering every sub-client
  method (sync + async), the session lifecycle, and the webhooks, plus live
  Multicard sandbox integration tests (`pytest -m live`).
- `CLAUDE.md` contributor/architecture guide and README Multicard sections.

### Changed

- `core/http.py` error logging now records only the HTTP status and host —
  response bodies and full URL paths (which can carry a card token) are no longer
  logged. Affects all gateways.
- Fixed the `makefile` obfuscate target path (`./payme/__init__.py` → `./tolov`).
- Package description and keywords now include Multicard.

### Fixed

- Kept `__version__` (`tolov/__init__.py`) in sync with `pyproject.toml`.

### Removed

- The non-functional `tolov[flask]` extra and the `HAS_FLASK` flag. There was
  never any Flask integration code — only Django and FastAPI are implemented.

### Security

- Multicard webhook handlers **fail closed** when no signing secret is configured,
  verify the MD5 callback signature in constant time, and reject callbacks whose
  `store_id` does not match the configured store.
- Removed sensitive data (PANs, card tokens, secrets) from error-path logs across
  all gateways.

[Unreleased]: https://github.com/ganiyevuz/tolov/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/ganiyevuz/tolov/releases/tag/v2.1.0
