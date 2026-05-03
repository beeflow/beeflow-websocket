"""copyright (c) 2014 - 2026 Beeflow Ltd.

Author Rafal Przetakowski <rafal.p@beeflow.co.uk>"""

from collections.abc import AsyncIterator
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from beeflow_websocket.core.event_registry import EventPluginProtocol
from beeflow_websocket.core.payloads import WebSocketActionPayload


class ActionContext(BaseModel):
    """Store connection-level data available to WebSocket actions during dispatch."""

    model_config = ConfigDict(frozen=True)

    websocket_id: str = Field(min_length=1)
    user_id: int = Field(gt=0)

    @field_validator("websocket_id")
    @classmethod
    def validate_websocket_id(cls, value: str) -> str:
        """Reject blank WebSocket connection identifiers."""
        normalised_value = value.strip()
        if normalised_value == "":
            raise ValueError("WebSocket connection identifier must not be blank.")

        return normalised_value


class ActionPluginProtocol(Protocol):
    """Define the async action handler contract used by WebSocket consumers."""

    def execute(
        self, message: WebSocketActionPayload, context: ActionContext
    ) -> AsyncIterator[EventPluginProtocol]: ...


class ActionRegistryMeta(type):
    """Register action classes under stable WebSocket action names."""

    REGISTRY: dict[str, type[ActionPluginProtocol]] = {}

    def __new__(
        mcs: type["ActionRegistryMeta"],
        class_name: str,
        bases: tuple[type, ...],
        attrs: dict[str, object],
        *,
        name: str | None = None,
    ) -> type[ActionPluginProtocol]:
        new_class = cast(type[ActionPluginProtocol], super().__new__(mcs, class_name, bases, attrs))

        # Registry entries must be created at class definition time so consumers can resolve actions deterministically.
        if attrs.get("__register__", True):
            plugin_name = name or attrs.get("__plugin_name__", class_name)
            if not isinstance(plugin_name, str):
                raise TypeError("Action plugin name must be a string.")

            mcs.REGISTRY[plugin_name] = new_class

        return new_class
