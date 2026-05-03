"""Django autodiscovered action fixtures."""

from collections.abc import AsyncIterator

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload


class DjangoAutodiscoveredAction(metaclass=ActionRegistryMeta, name="django_autodiscovered_action"):
    """Action registered by the Django autodiscovery hook."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield one health event for Django autodiscovery tests."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
