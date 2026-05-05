# Changelog

All notable changes to `beeflow-websocket` will be documented in this file.

This project follows Semantic Versioning.

## [Unreleased]

## [0.2.0] - 2026-05-05

### Added

- Django helper for reading access tokens passed through WebSocket subprotocols.

### Changed

- Django WebSocket consumer now selects only the non-secret authentication marker subprotocol during the handshake,
  avoiding token echoing in the accepted subprotocol.

## [0.1.1] - 2026-05-03

### Added

- Zero-config recursive plugin autodiscovery for user-defined actions, events, and recipients.
- Django autodiscovery that scans installed applications for conventional plugin modules such as `actions`, `events`,
  `recipients`, `ws.actions`, `ws.events`, and `ws.recipients`.
- FastAPI and Flask autodiscovery that scans the configuring application package and its parent packages for the same
  conventional plugin modules.

### Changed

- Documented which runtime packages are included in each install target and which deployment-specific packages users
  should add themselves.
- Autodiscovery now ignores absent conventional plugin modules while surfacing real import failures from existing
  packages during application startup.

## [0.1.0] - 2026-05-03

### Added

- Framework-independent WebSocket core with typed action, event, recipient, and payload contracts.
- Optional Django Channels adapter with authenticated WebSocket consumer, routing, event emitter, and Django app config.
- Optional FastAPI adapter with application-level configuration, WebSocket endpoint handler, and event emitter.
- Optional Flask adapter based on Flask-Sock with application-level configuration, WebSocket endpoint handler, and event emitter.
- Configurable Problem Details type base URL for framework adapters, with `about:blank` used when no application URL is configured.
- Separate core, Django, FastAPI, and Flask test and mypy Makefile targets.
- GitHub Actions workflow that builds, verifies, and publishes distributions to PyPI on pushes to `master`.
- Pull request CI workflow with required pre-commit, test, mypy, and build checks for `master` branch protection.

### Changed

- Kept framework dependencies behind optional extras so core-only installs do not require Django, Channels, FastAPI, or Flask.
