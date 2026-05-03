"""FastAPI configuration helpers for Beeflow WebSocket communication."""

from collections.abc import Iterable

from fastapi import FastAPI, WebSocket

from beeflow_websocket.core.autodiscover import (
    DEFAULT_AUTODISCOVER_MODULES,
    autodiscover_available_websocket_plugins,
    autodiscover_websocket_plugins,
    build_autodiscover_package_names,
    get_calling_module_name,
    get_module_base_packages,
    normalize_autodiscover_packages,
)

PROBLEM_TYPE_BASE_URL_STATE_KEY = "beeflow_websocket_problem_type_base_url"
AUTODISCOVER_STATE_KEY = "beeflow_websocket_autodiscover"
AUTODISCOVER_MODULES_STATE_KEY = "beeflow_websocket_autodiscover_modules"
AUTODISCOVER_PACKAGES_STATE_KEY = "beeflow_websocket_autodiscover_packages"


def configure_beeflow_websocket(
    app: FastAPI,
    *,
    problem_type_base_url: str | None = None,
    autodiscover: bool = True,
    autodiscover_modules: Iterable[str] | str | None = DEFAULT_AUTODISCOVER_MODULES,
    autodiscover_packages: Iterable[str] | str | None = None,
) -> None:
    """Store Beeflow WebSocket configuration on the FastAPI application state."""
    if not isinstance(autodiscover, bool):
        raise TypeError("FastAPI Beeflow WebSocket autodiscover setting must be a boolean.")

    normalized_packages = normalize_autodiscover_packages(
        autodiscover_packages,
        setting_name="FastAPI Beeflow WebSocket autodiscover packages",
    )
    normalized_modules = normalize_autodiscover_packages(
        autodiscover_modules,
        setting_name="FastAPI Beeflow WebSocket autodiscover modules",
    )

    setattr(app.state, PROBLEM_TYPE_BASE_URL_STATE_KEY, problem_type_base_url)
    setattr(app.state, AUTODISCOVER_STATE_KEY, autodiscover)
    setattr(app.state, AUTODISCOVER_MODULES_STATE_KEY, normalized_modules)
    setattr(app.state, AUTODISCOVER_PACKAGES_STATE_KEY, normalized_packages)

    if autodiscover:
        autodiscover_available_websocket_plugins(
            build_autodiscover_package_names(
                get_module_base_packages(get_calling_module_name(stack_depth=2)),
                normalized_modules,
            )
        )
        autodiscover_websocket_plugins(normalized_packages)


def get_problem_type_base_url(websocket: WebSocket) -> str | None:
    """Return the configured Problem Details type base URL from the FastAPI application state."""
    value = getattr(websocket.app.state, PROBLEM_TYPE_BASE_URL_STATE_KEY, None)
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("FastAPI Beeflow WebSocket problem type base URL must be a string or None.")

    return value
