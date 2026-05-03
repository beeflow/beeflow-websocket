# Changelog

All notable changes to `beeflow-websocket` will be documented in this file.

This project follows Semantic Versioning.

## [Unreleased]

### Added

- Framework-independent WebSocket core with typed action, event, recipient, and payload contracts.
- Optional Django Channels adapter with authenticated WebSocket consumer, routing, event emitter, and Django app config.
- Optional FastAPI adapter with application-level configuration, WebSocket endpoint handler, and event emitter.
- Optional Flask adapter based on Flask-Sock with application-level configuration, WebSocket endpoint handler, and event emitter.
- Configurable Problem Details type base URL for framework adapters, with `about:blank` used when no application URL is configured.
- Recursive plugin autodiscovery for user-defined actions, events, and recipients in Django, FastAPI, and Flask.
- Separate core, Django, FastAPI, and Flask test and mypy Makefile targets.
- GitHub Actions workflow that builds, verifies, and publishes distributions to PyPI on pushes to `master`.
- Pull request CI workflow with required pre-commit, test, mypy, and build checks for `master` branch protection.

### Changed

- Kept framework dependencies behind optional extras so core-only installs do not require Django, Channels, FastAPI, or Flask.
- Documented which runtime packages are included in each install target and which deployment-specific packages users
  should add themselves.
