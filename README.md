# Beeflow WebSocket

Beeflow WebSocket is a small Python library for action-driven WebSocket communication. It keeps reusable protocol code in `beeflow_websocket.core` and optional framework adapters, starting with Django Channels, under their own packages.

## Name

The proposed name is **Beeflow WebSocket**:

- package distribution: `beeflow-websocket`
- Python import: `beeflow_websocket`
- repository directory: `beeflow-websocket`

The name is direct because the package owns WebSocket action dispatch, event envelopes, recipient resolution, and optional transport adapters.

## Requirements

- Python 3.12 or newer
- uv for all project commands
- no pip workflow

## Installation

Core-only usage:

```bash
uv add beeflow-websocket
```

Django Channels usage after publishing the package:

```bash
uv add "beeflow-websocket[django]"
```

FastAPI projects can install the matching optional runtime extra:

```bash
uv add "beeflow-websocket[fastapi]"
```

Local development from this repository:

```bash
uv sync --extra dev
make test-core
make mypy-core
```

Django adapter development:

```bash
uv sync --extra dev --extra django --extra django-dev
make test-django
make mypy-django
```

## Protocol Flow

1. A client sends a `WebSocketActionPayload` envelope.
2. The Django consumer validates the transport-level shape.
3. `ActionRegistryMeta` resolves the action class.
4. The action yields zero, one, or many event objects.
5. `WebSocketEventEmitter` serialises each event to `WebSocketEventPayload`.
6. `RecipientRegistryMeta` resolves logical recipients into concrete WebSocket channel names.
7. The Django Channels adapter sends JSON to each resolved channel.

## Minimal Action

```python
from collections.abc import AsyncIterator

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload


class Health(metaclass=ActionRegistryMeta, name="health"):
    """Handle a health-check WebSocket action."""

    async def execute(
        self,
        message: WebSocketActionPayload,
        context: ActionContext,
    ) -> AsyncIterator[HealthEvent]:
        """Yield a response event for the current WebSocket connection."""
        yield HealthEvent(
            recipient="websocket",
            recipient_id=context.websocket_id,
            req_id=message.req_id,
        )
```

## Django Channels Setup

Add the package to Django settings when using the adapter:

```python
INSTALLED_APPS = [
    "channels",
    "beeflow_websocket.django",
]
```

Include the bundled WebSocket route in your ASGI routing:

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from beeflow_websocket.django.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(websocket_urlpatterns),
    }
)
```

The bundled route is `ws/`. The default consumer accepts only authenticated users.

## Documentation

English documentation starts at [`docs/en/README.md`](docs/en/README.md).
Polish documentation starts at [`docs/pl/README.md`](docs/pl/README.md).

## Development

Use uv only:

```bash
uv sync --extra dev --extra django --extra django-dev
make test
make mypy
uv build
```
