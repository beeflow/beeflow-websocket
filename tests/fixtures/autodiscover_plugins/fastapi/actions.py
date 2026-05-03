"""FastAPI autodiscovered action fixtures."""

from collections.abc import AsyncIterator

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload


class FastAPIAutodiscoveredAction(metaclass=ActionRegistryMeta, name="fastapi_autodiscovered_action"):
    """Action registered by the FastAPI configuration helper."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield one health event for FastAPI autodiscovery tests."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
