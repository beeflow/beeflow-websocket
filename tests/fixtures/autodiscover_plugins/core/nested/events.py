"""Autodiscovered event fixtures."""

from uuid import UUID

from beeflow_websocket.core.event_registry import EventRegistryMeta
from beeflow_websocket.core.payloads import WebSocketEventPayload


class CoreAutodiscoveredEvent(metaclass=EventRegistryMeta, name="core_autodiscovered_event"):
    """Event registered when its nested module is imported by autodiscovery."""

    def __init__(self, req_id: UUID) -> None:
        """Store the request identifier for the fixture event."""
        self.req_id = req_id

    async def emit(self) -> WebSocketEventPayload:
        """Return one event payload for autodiscovery tests."""
        return WebSocketEventPayload(
            req_id=self.req_id,
            event="core_autodiscovered_event",
            recipient="core_autodiscovered_recipient",
            recipient_id="core.autodiscovered",
            payload={},
        )
