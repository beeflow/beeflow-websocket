"""Flask configuration helpers for Beeflow WebSocket communication."""

from collections.abc import Iterable

from flask import Flask, current_app

from beeflow_websocket.core.autodiscover import (
    DEFAULT_AUTODISCOVER_MODULES,
    autodiscover_available_websocket_plugins,
    autodiscover_websocket_plugins,
    build_autodiscover_package_names,
    get_calling_module_name,
    get_module_base_packages,
    normalize_autodiscover_packages,
)

PROBLEM_TYPE_BASE_URL_CONFIG_KEY = "BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL"
AUTODISCOVER_CONFIG_KEY = "BEEFLOW_WEBSOCKET_AUTODISCOVER"
AUTODISCOVER_MODULES_CONFIG_KEY = "BEEFLOW_WEBSOCKET_AUTODISCOVER_MODULES"
AUTODISCOVER_PACKAGES_CONFIG_KEY = "BEEFLOW_WEBSOCKET_AUTODISCOVER_PACKAGES"


def configure_beeflow_websocket(
    app: Flask,
    *,
    problem_type_base_url: str | None = None,
    autodiscover: bool = True,
    autodiscover_modules: Iterable[str] | str | None = DEFAULT_AUTODISCOVER_MODULES,
    autodiscover_packages: Iterable[str] | str | None = None,
) -> None:
    """Store Beeflow WebSocket configuration on the Flask application config."""
    if not isinstance(autodiscover, bool):
        raise TypeError("Flask Beeflow WebSocket autodiscover setting must be a boolean.")

    normalized_packages = normalize_autodiscover_packages(
        autodiscover_packages,
        setting_name="Flask Beeflow WebSocket autodiscover packages",
    )
    normalized_modules = normalize_autodiscover_packages(
        autodiscover_modules,
        setting_name="Flask Beeflow WebSocket autodiscover modules",
    )

    app.config[PROBLEM_TYPE_BASE_URL_CONFIG_KEY] = problem_type_base_url
    app.config[AUTODISCOVER_CONFIG_KEY] = autodiscover
    app.config[AUTODISCOVER_MODULES_CONFIG_KEY] = normalized_modules
    app.config[AUTODISCOVER_PACKAGES_CONFIG_KEY] = normalized_packages

    if autodiscover:
        autodiscover_available_websocket_plugins(
            build_autodiscover_package_names(
                get_module_base_packages(app.import_name)
                + get_module_base_packages(get_calling_module_name(stack_depth=2)),
                normalized_modules,
            )
        )
        autodiscover_websocket_plugins(normalized_packages)


def get_problem_type_base_url() -> str | None:
    """Return the configured Problem Details type base URL from the active Flask app."""
    value = current_app.config.get(PROBLEM_TYPE_BASE_URL_CONFIG_KEY)
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("Flask Beeflow WebSocket problem type base URL must be a string or None.")

    return value
