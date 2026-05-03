"""Flask installed-app action fixtures."""

from collections.abc import AsyncIterator

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload


class InstalledFlaskAutodiscoveredAction(metaclass=ActionRegistryMeta, name="installed_flask_autodiscovered_action"):
    """Action registered from the Flask app package without package settings."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield one health event for Flask conventional autodiscovery tests."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
