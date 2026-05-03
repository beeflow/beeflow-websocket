"""FastAPI configuration helpers for Beeflow WebSocket communication."""

from fastapi import FastAPI, WebSocket

PROBLEM_TYPE_BASE_URL_STATE_KEY = "beeflow_websocket_problem_type_base_url"


def configure_beeflow_websocket(app: FastAPI, *, problem_type_base_url: str | None = None) -> None:
    """Store Beeflow WebSocket configuration on the FastAPI application state."""
    setattr(app.state, PROBLEM_TYPE_BASE_URL_STATE_KEY, problem_type_base_url)


def get_problem_type_base_url(websocket: WebSocket) -> str | None:
    """Return the configured Problem Details type base URL from the FastAPI application state."""
    value = getattr(websocket.app.state, PROBLEM_TYPE_BASE_URL_STATE_KEY, None)
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("FastAPI Beeflow WebSocket problem type base URL must be a string or None.")

    return value
