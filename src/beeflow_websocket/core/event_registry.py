"""copyright (c) 2014 - 2026 Beeflow Ltd.

Author Rafal Przetakowski <rafal.p@beeflow.co.uk>"""

from typing import Protocol, cast

from beeflow_websocket.core.payloads import WebSocketEventPayload


class EventPluginProtocol(Protocol):
    """Define the async event emitter contract used by WebSocket consumers."""

    async def emit(self) -> WebSocketEventPayload: ...


class EventRegistryMeta(type):
    """Register event classes under stable WebSocket event names."""

    REGISTRY: dict[str, type[EventPluginProtocol]] = {}

    def __new__(
        mcs: type["EventRegistryMeta"],
        class_name: str,
        bases: tuple[type, ...],
        attrs: dict[str, object],
        *,
        name: str | None = None,
    ) -> type[EventPluginProtocol]:
        new_class = cast(type[EventPluginProtocol], super().__new__(mcs, class_name, bases, attrs))

        # Registry entries must be created at class definition time so emitters can resolve events deterministically.
        if attrs.get("__register__", True):
            plugin_name = name or attrs.get("__plugin_name__", class_name)
            if not isinstance(plugin_name, str):
                raise TypeError("Event plugin name must be a string.")

            mcs.REGISTRY[plugin_name] = new_class

        return new_class
