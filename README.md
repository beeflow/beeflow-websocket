# Beeflow WebSocket

Beeflow WebSocket is a small Python library for action-driven WebSocket communication. It keeps reusable protocol code in `beeflow_websocket.core` and optional framework adapters under their own packages.

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

Flask projects can install the matching optional runtime extra:

```bash
uv add "beeflow-websocket[flask]"
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

FastAPI adapter development:

```bash
uv sync --extra dev --extra fastapi --extra fastapi-dev
make test-fastapi
make mypy-fastapi
```

Flask adapter development:

```bash
uv sync --extra dev --extra flask --extra flask-dev
make test-flask
make mypy-flask
```

## Protocol Flow

1. A client sends a `WebSocketActionPayload` envelope.
2. The framework adapter validates the transport-level shape.
3. `ActionRegistryMeta` resolves the action class.
4. The action yields zero, one, or many event objects.
5. The adapter emitter serialises each event to `WebSocketEventPayload`.
6. `RecipientRegistryMeta` resolves logical recipients into concrete WebSocket identifiers.
7. The framework adapter sends JSON to each resolved WebSocket target.

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

BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL = "https://example.com/problems/websocket"
```

If `BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL` is not configured, error payloads use `about:blank` as their Problem
Details `type`.

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

## FastAPI Setup

Install the optional FastAPI extra:

```bash
uv add "beeflow-websocket[fastapi]"
```

Add a WebSocket route and pass the authenticated user id from your own FastAPI dependency:

```python
from fastapi import FastAPI, WebSocket

from beeflow_websocket.fastapi import configure_beeflow_websocket, handle_beeflow_websocket

app = FastAPI()
configure_beeflow_websocket(app, problem_type_base_url="https://example.com/problems/websocket")


@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await handle_beeflow_websocket(websocket, user_id=1)
```

The FastAPI adapter handles the current WebSocket connection directly. Cross-connection broadcast or external pub/sub belongs in a separate connection manager.
If the FastAPI app is not configured with a problem type base URL, error payloads use `about:blank` as their Problem
Details `type`.

## Flask Setup

Install the optional Flask extra:

```bash
uv add "beeflow-websocket[flask]"
```

Add a `Flask-Sock` WebSocket route and pass the authenticated user id from your own Flask auth layer:

```python
from flask import Flask
from flask_sock import Sock

from beeflow_websocket.flask import configure_beeflow_websocket, handle_beeflow_websocket

app = Flask(__name__)
sock = Sock(app)
configure_beeflow_websocket(app, problem_type_base_url="https://example.com/problems/websocket")


@sock.route("/ws/")
def websocket_endpoint(websocket) -> None:
    handle_beeflow_websocket(websocket, user_id=1)
```

The Flask adapter handles the current WebSocket connection directly. Cross-connection broadcast or external pub/sub
belongs in a separate connection manager. If the Flask app is not configured with a problem type base URL, error
payloads use `about:blank` as their Problem Details `type`.

## Documentation

English documentation starts at [`docs/en/README.md`](docs/en/README.md).
Polish documentation starts at [`docs/pl/README.md`](docs/pl/README.md).

## Development

Use uv only:

```bash
uv sync --extra dev --extra django --extra django-dev --extra fastapi --extra fastapi-dev --extra flask --extra flask-dev
make test
make mypy
uv build
```

## Release Automation

Every push to `master` runs `.github/workflows/publish.yml`. The workflow tests all adapters, runs mypy, builds the
source distribution and wheel, then publishes the built distributions to PyPI through Trusted Publishing.

Pull requests targeting `master` run `.github/workflows/ci.yml`, which checks the lockfile, runs tests, runs mypy, and
verifies that distributions build. The workflow also runs pre-commit hooks.

Configure PyPI Trusted Publishing for:

- owner: `beeflow`
- repository: `beeflow-websocket`
- workflow: `publish.yml`
- environment: `pypi`

PyPI package versions are immutable. Bump `project.version` in `pyproject.toml` before merging changes that should be
published.

The `master` branch is protected on GitHub. Code changes must go through a pull request and review before they can be
merged. Required pull request checks are `Pre-commit`, `Test`, `Mypy`, and `Build`.

Manual patch release bump example:

```toml
[project]
version = "0.1.1"
```

Move the relevant changelog entries from `[Unreleased]` into a dated release section:

```markdown
## [0.1.1] - 2026-05-03

### Added

- Added FastAPI and Flask adapters.
```

Verify before merging:

```bash
make test
make mypy
uv build
```
