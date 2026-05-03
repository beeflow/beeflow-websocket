"""Flask configuration helpers for Beeflow WebSocket communication."""

from flask import Flask, current_app

PROBLEM_TYPE_BASE_URL_CONFIG_KEY = "BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL"


def configure_beeflow_websocket(app: Flask, *, problem_type_base_url: str | None = None) -> None:
    """Store Beeflow WebSocket configuration on the Flask application config."""
    app.config[PROBLEM_TYPE_BASE_URL_CONFIG_KEY] = problem_type_base_url


def get_problem_type_base_url() -> str | None:
    """Return the configured Problem Details type base URL from the active Flask app."""
    value = current_app.config.get(PROBLEM_TYPE_BASE_URL_CONFIG_KEY)
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("Flask Beeflow WebSocket problem type base URL must be a string or None.")

    return value
