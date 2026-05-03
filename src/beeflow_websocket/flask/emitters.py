"""Flask WebSocket event emitters for Beeflow WebSocket communication."""

import json
from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from beeflow_websocket.core.event_registry import EventPluginProtocol
from beeflow_websocket.core.recipient_registry import RecipientMapDoesNotExist, RecipientRegistryMeta

MessageIdFactory = Callable[[], UUID]
SequenceProvider = Callable[[], int]


class FlaskWebSocketProtocol(Protocol):
    """Define the Flask-Sock WebSocket send contract required by the emitter."""

    def send(self, data: str) -> None: ...


class FlaskWebSocketEventEmitter:
    """Emit registered events through the current Flask WebSocket connection."""

    def __init__(
        self,
        websocket: FlaskWebSocketProtocol,
        websocket_id: str,
        message_id_factory: MessageIdFactory,
        sequence_provider: SequenceProvider,
    ) -> None:
        """Store the WebSocket connection used to publish event payloads."""
        self.websocket = websocket
        self.websocket_id = websocket_id
        self.message_id_factory = message_id_factory
        self.sequence_provider = sequence_provider

    async def emit(self, event: EventPluginProtocol) -> None:
        """Serialise and send an event payload when it targets the current WebSocket."""
        payload = (await event.emit()).with_dispatch_metadata(
            msg_id=self.message_id_factory(),
            seq=self.sequence_provider(),
        )
        recipient_class = RecipientRegistryMeta.REGISTRY.get(payload.recipient)
        if recipient_class is None:
            raise RecipientMapDoesNotExist

        websocket_ids = await recipient_class().resolve(payload.recipient_id)
        if self.websocket_id not in websocket_ids:
            return

        self.websocket.send(json.dumps(payload.to_dict()))
