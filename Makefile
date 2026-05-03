.PHONY: test test-core test-django mypy mypy-core mypy-django build publish

test: test-core test-django

test-core:
	uv run --extra dev pytest tests/core

test-django:
	uv run --extra dev --extra django --extra django-dev pytest tests/django

mypy: mypy-core mypy-django

mypy-core:
	uv run --extra dev mypy

mypy-django:
	uv run --extra dev --extra django --extra django-dev mypy src/beeflow_websocket/django

build:
	uv build

publish: build
	uv publish dist/*.tar.gz dist/*.whl
