"""Direct WebSocket recipient resolver for Beeflow WebSocket communication."""

from beeflow_websocket.core.recipient_registry import RecipientRegistryMeta

WEBSOCKET_RECIPIENT = "websocket"


class WebSocketRecipient(metaclass=RecipientRegistryMeta, name=WEBSOCKET_RECIPIENT):
    """Resolve direct WebSocket recipients into concrete channel names."""

    async def resolve(self, recipient_id: str) -> tuple[str, ...]:
        """Resolve a direct WebSocket recipient into one concrete channel name."""
        return (recipient_id,)
