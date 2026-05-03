.PHONY: test test-core test-django test-fastapi test-flask
.PHONY: mypy mypy-core mypy-django mypy-fastapi mypy-flask pre-commit
.PHONY: build publish

test: test-core test-django test-fastapi test-flask

test-core:
	uv run --extra dev pytest tests/core

test-django:
	uv run --extra dev --extra django --extra django-dev pytest tests/django

test-fastapi:
	uv run --extra dev --extra fastapi --extra fastapi-dev pytest tests/fastapi

test-flask:
	uv run --extra dev --extra flask --extra flask-dev pytest tests/flask

mypy: mypy-core mypy-django mypy-fastapi mypy-flask

mypy-core:
	uv run --extra dev mypy

mypy-django:
	uv run --extra dev --extra django --extra django-dev mypy src/beeflow_websocket/django

mypy-fastapi:
	uv run --extra dev --extra fastapi mypy src/beeflow_websocket/fastapi

mypy-flask:
	uv run --extra dev --extra flask mypy src/beeflow_websocket/flask

pre-commit:
	uv run pre-commit run --all-files

build:
	uv build

publish: build
	uv publish dist/*.tar.gz dist/*.whl
