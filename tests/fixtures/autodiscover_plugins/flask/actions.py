"""Flask autodiscovered action fixtures."""

from collections.abc import AsyncIterator

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload


class FlaskAutodiscoveredAction(metaclass=ActionRegistryMeta, name="flask_autodiscovered_action"):
    """Action registered by the Flask configuration helper."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield one health event for Flask autodiscovery tests."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
