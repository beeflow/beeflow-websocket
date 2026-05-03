"""Health-check events for Beeflow WebSocket communication."""

from uuid import UUID

from beeflow_websocket.core.event_registry import EventRegistryMeta
from beeflow_websocket.core.payloads import WebSocketEventPayload


class HealthEvent(metaclass=EventRegistryMeta, name="health"):
    """Emit the health-check WebSocket response."""

    def __init__(self, recipient: str, recipient_id: str, req_id: UUID) -> None:
        """Store the target recipient used by the event dispatcher."""
        self.recipient = recipient
        self.recipient_id = recipient_id
        self.req_id = req_id

    async def emit(self) -> WebSocketEventPayload:
        """Return a minimal successful WebSocket health response."""
        return WebSocketEventPayload(
            req_id=self.req_id,
            event="health",
            recipient=self.recipient,
            recipient_id=self.recipient_id,
            payload={"status": "ok"},
        )
