"""WebSocket event emitters for Beeflow WebSocket communication."""

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from beeflow_websocket.core.event_registry import EventPluginProtocol
from beeflow_websocket.core.recipient_registry import RecipientMapDoesNotExist, RecipientRegistryMeta


class WebSocketChannelLayerProtocol(Protocol):
    """Define the channel layer contract required by the WebSocket event emitter."""

    async def send(self, channel: str, message: dict[str, object]) -> None: ...


MessageIdFactory = Callable[[], UUID]
SequenceProvider = Callable[[], int]


class WebSocketEventEmitter:
    """Emit registered events through WebSocket channels resolved by the recipient registry."""

    def __init__(
        self,
        channel_layer: WebSocketChannelLayerProtocol,
        message_id_factory: MessageIdFactory,
        sequence_provider: SequenceProvider,
    ) -> None:
        """Store the channel layer used to publish WebSocket event payloads."""
        self.channel_layer = channel_layer
        self.message_id_factory = message_id_factory
        self.sequence_provider = sequence_provider

    async def emit(self, event: EventPluginProtocol) -> None:
        """Serialise and route a WebSocket event payload to concrete WebSocket channels."""
        payload = (await event.emit()).with_dispatch_metadata(
            msg_id=self.message_id_factory(),
            seq=self.sequence_provider(),
        )
        recipient_class = RecipientRegistryMeta.REGISTRY.get(payload.recipient)
        if recipient_class is None:
            raise RecipientMapDoesNotExist

        for websocket_id in await recipient_class().resolve(payload.recipient_id):
            await self.channel_layer.send(
                websocket_id,
                {
                    "type": "beeflow.websocket.event",
                    "payload": payload.to_dict(),
                },
            )
