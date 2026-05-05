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

## Runtime Dependencies

Each install target keeps only the dependencies needed by that adapter. Deployment servers, channel backends,
external pub/sub, and application-level auth remain the responsibility of the application using the package.

| Install target | Installed by this package | Not installed | Add when needed |
| --- | --- | --- | --- |
| `beeflow-websocket` | `pydantic` | Django, Channels, FastAPI, Flask, WebSocket servers | Add a framework extra when the project uses a supported adapter. |
| `beeflow-websocket[django]` | `django`, `channels` | `daphne`, `channels-redis`, Redis server | Add `daphne` when serving Django Channels with Daphne. Add `channels-redis` and Redis when using a Redis channel layer for groups, multi-process workers, or cross-instance delivery. |
| `beeflow-websocket[fastapi]` | `fastapi` | ASGI servers such as `uvicorn` or `hypercorn`, external pub/sub, connection managers | Add an ASGI server if the application does not already provide one. Add Redis or another pub/sub layer only when broadcasting across connections, workers, or instances. |
| `beeflow-websocket[flask]` | `flask`, `flask-sock` | Production servers such as `gunicorn`, external pub/sub, connection managers | Add the production server used by the application deployment. Add Redis or another pub/sub layer only when broadcasting across connections, workers, or instances. |

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

## Plugin Autodiscover

Action, event, and recipient classes are registered when their modules are imported. Autodiscovery imports
application-owned plugin modules during startup so their registry metaclasses can run.

Autodiscovery is enabled by default. Django scans every installed Django app. FastAPI and Flask scan the package that
called `configure_beeflow_websocket` and its parent packages. Each adapter imports these conventional plugin modules
when they exist:

```text
my_app/actions.py
my_app/events.py
my_app/recipients.py
my_app/ws/actions.py
my_app/ws/events.py
my_app/ws/recipients.py
```

Missing modules are ignored. Import errors inside existing modules are not hidden; a broken plugin module should fail
application startup.

FastAPI and Flask do not need autodiscovery configuration for this conventional layout:

```python
configure_beeflow_websocket(
    app,
    problem_type_base_url="https://example.com/problems/websocket",
)
```

Set `BEEFLOW_WEBSOCKET_AUTODISCOVER = False` in Django or `autodiscover=False` in FastAPI and Flask to disable startup
imports.

## Django Channels Setup

Install the optional Django extra:

```bash
uv add "beeflow-websocket[django]"
```

Add the package and Channels settings in `settings.py`:

```python
INSTALLED_APPS = [
    "channels",
    "beeflow_websocket.django",
    # ...
]

ASGI_APPLICATION = "config.asgi.application"

BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL = "https://example.com/problems/websocket"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
```

If `BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL` is not configured, error payloads use `about:blank` as their Problem
Details `type`. Use the in-memory channel layer only for local development and single-process testing. For production
or multi-process delivery, install `channels-redis` and use a Redis channel layer:

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    }
}
```

WebSocket routing belongs in `asgi.py`, not in `urls.py`. Include the bundled route with Channels auth middleware when
the project uses standard Django session/cookie authentication:

```python
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from beeflow_websocket.django.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns),
            )
        ),
    }
)
```

The bundled route is `ws/`, so the client connects to `/ws/`. The default consumer accepts only authenticated users.
`AuthMiddlewareStack` sets `scope["user"]` for standard Django session/cookie authentication.

To use a different path, define your own WebSocket URL patterns and still mount them in `asgi.py`:

```python
from django.urls import path

from beeflow_websocket.django.consumer import WebSocketConsumer

websocket_urlpatterns = [
    path("api/ws/", WebSocketConsumer.as_asgi()),
]
```

Then mount that local `websocket_urlpatterns` in `URLRouter(...)` instead of importing
`beeflow_websocket.django.routing.websocket_urlpatterns`.

Do not send access tokens in the WebSocket query string. Query-string tokens can leak through logs, browser history,
proxy logs, and monitoring tools. If browser clients authenticate with an access token, send the public marker and then
the secret token as WebSocket subprotocols:

```javascript
const socket = new WebSocket("wss://example.com/ws/", ["access-token", accessToken]);
```

Use the bundled `AccessTokenAuthMiddleware` to read that token and populate `scope["user"]`. The library extracts the
token and selects only the non-secret `access-token` marker during the handshake. The application provides only the
token validation function because signing keys, JWT claims, user models, and revocation rules are project-owned:

```python
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from beeflow_websocket.django.authentication import AccessTokenAuthMiddleware
from beeflow_websocket.django.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()


async def get_user_for_access_token(token: str) -> object:
    """Validate the project access token and return a Django user."""
    ...


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AccessTokenAuthMiddleware(
                URLRouter(websocket_urlpatterns),
                user_resolver=get_user_for_access_token,
            )
        ),
    }
)
```

`AccessTokenAuthMiddleware` accepts sync and async resolvers. Synchronous resolvers run through Channels
`database_sync_to_async`, so regular Django ORM lookups do not run on the ASGI event loop. The resolver must return an
object compatible with the consumer contract: `user.is_authenticated` must be true and `user.id` must contain the
application user id. When the client does not send an access token, the middleware sets an anonymous user and the
default consumer closes the connection.

## FastAPI Setup

Install the optional FastAPI extra:

```bash
uv add "beeflow-websocket[fastapi]"
```

FastAPI routing stays in the application. Configure the adapter once, add a WebSocket route, authenticate the
connection in your own dependency, and pass the authenticated user id to the handler:

```python
from fastapi import Depends, FastAPI, WebSocket

from beeflow_websocket.fastapi import configure_beeflow_websocket, handle_beeflow_websocket

app = FastAPI()
configure_beeflow_websocket(
    app,
    problem_type_base_url="https://example.com/problems/websocket",
)


async def get_current_user_id(websocket: WebSocket) -> int:
    """Authenticate the WebSocket connection and return the project user id."""
    ...


@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket, user_id: int = Depends(get_current_user_id)) -> None:
    await handle_beeflow_websocket(websocket, user_id=user_id)
```

The route path is fully controlled by the application. Use `@app.websocket("/api/ws/")` or any other path when the
project does not want `/ws/`. The FastAPI adapter handles the current WebSocket connection directly and accepts it
inside `handle_beeflow_websocket`. Cross-connection broadcast, connection registries, and external pub/sub belong in
the application layer.

If the FastAPI app is not configured with a problem type base URL, error payloads use `about:blank` as their Problem
Details `type`. Run the app with the ASGI server already used by the project, for example `uvicorn my_app.main:app`.

## Flask Setup

Install the optional Flask extra:

```bash
uv add "beeflow-websocket[flask]"
```

Flask routing stays in the application. Configure the adapter once, add a `Flask-Sock` WebSocket route, authenticate the
connection in your own Flask auth layer, and pass the authenticated user id to the handler:

```python
from flask import Flask, g
from flask_sock import Sock

from beeflow_websocket.flask import configure_beeflow_websocket, handle_beeflow_websocket

app = Flask(__name__)
sock = Sock(app)
configure_beeflow_websocket(
    app,
    problem_type_base_url="https://example.com/problems/websocket",
)


@sock.route("/ws/")
def websocket_endpoint(websocket) -> None:
    user_id = g.user.id

    handle_beeflow_websocket(websocket, user_id=user_id)
```

The route path is fully controlled by the application. Use `@sock.route("/api/ws/")` or any other path when the project
does not want `/ws/`. The Flask adapter handles the current WebSocket connection directly. Cross-connection broadcast,
connection registries, and external pub/sub belong in the application layer.

If the Flask app is not configured with a problem type base URL, error payloads use `about:blank` as their Problem
Details `type`. Use the production server already chosen by the Flask project and make sure it supports WebSocket
traffic for `Flask-Sock`.

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
