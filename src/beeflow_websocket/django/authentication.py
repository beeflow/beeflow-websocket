"""Django WebSocket authentication helpers."""

from collections.abc import Iterable, Mapping

AUTHENTICATION_SUBPROTOCOL = "access-token"


def access_token_from_subprotocols(scope: Mapping[str, object]) -> str:
    """Return the access token sent after the Beeflow authentication subprotocol marker."""
    subprotocols = _subprotocols_from_scope(scope)
    if AUTHENTICATION_SUBPROTOCOL not in subprotocols:
        return ""

    token_index = subprotocols.index(AUTHENTICATION_SUBPROTOCOL) + 1

    return subprotocols[token_index] if token_index < len(subprotocols) else ""


def selected_authentication_subprotocol(scope: Mapping[str, object]) -> str | None:
    """Return the non-secret authentication subprotocol selected for the WebSocket handshake."""
    subprotocols = _subprotocols_from_scope(scope)

    return AUTHENTICATION_SUBPROTOCOL if AUTHENTICATION_SUBPROTOCOL in subprotocols else None


def _subprotocols_from_scope(scope: Mapping[str, object]) -> list[str]:
    subprotocols = scope.get("subprotocols", [])
    if isinstance(subprotocols, str) or not isinstance(subprotocols, Iterable):
        return []

    return [subprotocol for subprotocol in subprotocols if isinstance(subprotocol, str)]
