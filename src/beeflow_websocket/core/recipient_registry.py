"""Recipient class registry for Beeflow WebSocket communication."""

from typing import Protocol, cast


class RecipientMapDoesNotExist(Exception):
    """Raise when no recipient resolver exists for the event recipient type."""


class RecipientPluginProtocol(Protocol):
    """Define the async recipient resolver contract used by WebSocket event dispatch."""

    async def resolve(self, recipient_id: str) -> tuple[str, ...]: ...


class RecipientRegistryMeta(type):
    """Register recipient resolver classes under stable WebSocket recipient names."""

    REGISTRY: dict[str, type[RecipientPluginProtocol]] = {}

    def __new__(
        mcs: type["RecipientRegistryMeta"],
        class_name: str,
        bases: tuple[type, ...],
        attrs: dict[str, object],
        *,
        name: str | None = None,
    ) -> type[RecipientPluginProtocol]:
        new_class = cast(type[RecipientPluginProtocol], super().__new__(mcs, class_name, bases, attrs))

        # Registry entries must be created at class definition time so emitters can resolve recipients consistently.
        if attrs.get("__register__", True):
            plugin_name = name or attrs.get("__plugin_name__", class_name)
            if not isinstance(plugin_name, str):
                raise TypeError("Recipient plugin name must be a string.")

            mcs.REGISTRY[plugin_name] = new_class

        return new_class
