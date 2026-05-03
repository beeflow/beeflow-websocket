"""copyright (c) 2014 - 2026 Beeflow Ltd.

Author Rafal Przetakowski <rafal.p@beeflow.co.uk>"""

from collections.abc import AsyncIterator

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload


class Health(metaclass=ActionRegistryMeta, name="health"):
    """Handle the health-check WebSocket action."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield the event confirming that WebSocket dispatch works."""
        yield HealthEvent(
            recipient="websocket",
            recipient_id=context.websocket_id,
            req_id=message.req_id,
        )
