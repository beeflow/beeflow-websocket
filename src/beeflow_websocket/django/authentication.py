"""Django WebSocket authentication helpers."""

from collections.abc import Awaitable, Callable, Iterable, Mapping
from inspect import iscoroutinefunction
from typing import Any

from channels.db import database_sync_to_async

ASGIScope = dict[str, Any]
ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApplication = Callable[[ASGIScope, ASGIReceive, ASGISend], Awaitable[None]]
TokenUserResolver = Callable[[str], object | Awaitable[object]]

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


class AccessTokenAuthMiddleware:
    """Resolve a WebSocket access-token subprotocol into ``scope["user"]``."""

    def __init__(self, app: ASGIApplication, user_resolver: TokenUserResolver) -> None:
        """Create middleware with a project-owned token-to-user resolver."""
        self.app = app
        self.user_resolver = user_resolver
        self.is_async_user_resolver = _is_async_callable(user_resolver)

    async def __call__(self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend) -> None:
        """Populate the ASGI scope user before the WebSocket consumer runs."""
        scope = dict(scope)
        token = access_token_from_subprotocols(scope)
        scope["user"] = await self._user_from_token(token) if token else self._anonymous_user()

        await self.app(scope, receive, send)

    async def _user_from_token(self, token: str) -> object:
        if self.is_async_user_resolver:
            resolved_user = self.user_resolver(token)
            if isinstance(resolved_user, Awaitable):
                return await resolved_user

            return resolved_user

        return await database_sync_to_async(self.user_resolver)(token)

    def _anonymous_user(self) -> object:
        return _AnonymousWebSocketUser()


class _AnonymousWebSocketUser:
    is_authenticated: bool = False


def _subprotocols_from_scope(scope: Mapping[str, object]) -> list[str]:
    subprotocols = scope.get("subprotocols", [])
    if isinstance(subprotocols, str) or not isinstance(subprotocols, Iterable):
        return []

    return [subprotocol for subprotocol in subprotocols if isinstance(subprotocol, str)]


def _is_async_callable(resolver: TokenUserResolver) -> bool:
    return iscoroutinefunction(resolver) or iscoroutinefunction(getattr(resolver, "__call__", None))
