# Beeflow WebSocket

## Purpose

`beeflow_websocket` is a reusable WebSocket action and event layer for Python services. It receives client actions, dispatches them to registered action classes, and sends events emitted by those actions.

The bundled Django Channels route is:

```text
ws/
```

The default Django consumer accepts connections only for authenticated users.

## Flow

1. The client opens a WebSocket connection.
2. The client sends an action wrapped in `WebSocketActionPayload`.
3. The consumer resolves the action class through `ActionRegistryMeta`.
4. The action executes its logic and emits zero, one, or many events with `yield`.
5. `WebSocketEventEmitter` serialises the event into `WebSocketEventPayload`.
6. The emitter resolves the recipient through `RecipientRegistryMeta`.
7. The recipient resolver returns concrete WebSocket identifiers.
8. The emitter sends JSON to the resolved connections.

## Internal Split

The communication layer is split into core and optional framework adapters:

```text
beeflow_websocket/
  core/
  django/
  fastapi/
  flask/
```

`core` contains framework-independent elements:

- Pydantic payloads
- action, event, and recipient registries
- the `ActionContext` contract
- action, event, and recipient contracts
- shared actions, events, and recipients independent from transport

`django` contains the Django Channels integration:

- WebSocket consumer
- WebSocket routing
- emitter sending events through Channel Layer
- backend `msg_id` generation
- per-connection WebSocket `seq` counter

`fastapi` contains the FastAPI integration:

- WebSocket endpoint handler
- application configuration helper storing settings on `app.state`
- emitter sending events through the current WebSocket connection
- backend `msg_id` generation
- per-connection WebSocket `seq` counter

The FastAPI adapter handles direct responses on the current WebSocket connection. Cross-connection broadcast or
external pub/sub belongs in a separate connection manager.

`flask` contains the Flask-Sock integration:

- WebSocket endpoint handler
- application configuration helper storing settings in `app.config`
- emitter sending events through the current WebSocket connection
- backend `msg_id` generation
- per-connection WebSocket `seq` counter

The Flask adapter handles direct responses on the current WebSocket connection. Cross-connection broadcast or external
pub/sub belongs in a separate connection manager.

Modules in `core` do not import Django, Channels, FastAPI, or Flask. Domain code should import contracts and registries from `beeflow_websocket.core`.
Future adapters should live beside `django` instead of importing framework code into `core`.

## Runtime Dependencies

The package keeps framework integrations optional:

| Install target | Installed by this package | Not installed | Add when needed |
| --- | --- | --- | --- |
| `beeflow-websocket` | `pydantic` | Django, Channels, FastAPI, Flask, WebSocket servers | Add a framework extra when the project uses a supported adapter. |
| `beeflow-websocket[django]` | `django`, `channels` | `daphne`, `channels-redis`, Redis server | Add `daphne` when serving Django Channels with Daphne. Add `channels-redis` and Redis when using a Redis channel layer for groups, multi-process workers, or cross-instance delivery. |
| `beeflow-websocket[fastapi]` | `fastapi` | ASGI servers such as `uvicorn` or `hypercorn`, external pub/sub, connection managers | Add an ASGI server if the application does not already provide one. Add Redis or another pub/sub layer only when broadcasting across connections, workers, or instances. |
| `beeflow-websocket[flask]` | `flask`, `flask-sock` | Production servers such as `gunicorn`, external pub/sub, connection managers | Add the production server used by the application deployment. Add Redis or another pub/sub layer only when broadcasting across connections, workers, or instances. |

## Input Contract

Every message received from the client has this shape:

```json
{
  "msg_id": "client-message-uuid",
  "req_id": "client-request-uuid",
  "action": "health",
  "payload": {}
}
```

`msg_id` identifies one client message. `req_id` identifies the client request and must be copied into events and errors produced by that request. `action` points to a registered action name. `payload` belongs to the specific action.

## Communication Consistency

`msg_id`, `req_id`, and `seq` have separate roles:

- client `msg_id` identifies one incoming message
- backend `msg_id` is generated separately for every outgoing message
- `req_id` correlates a client request with events and errors produced by that request
- `seq` is assigned by the backend for outgoing events on the current WebSocket connection

`req_id` rules:

1. a valid client action must contain a non-empty `req_id`
2. every event produced by that action returns the same `req_id`
3. every error produced by that action returns the same `req_id`
4. a message without a valid `req_id` is invalid and is not dispatched to an action

`seq` is added by `WebSocketEventEmitter`. `ErrorPayload` errors do not use `seq`.

## Output Contract

Every event sent to the client has this shape:

```json
{
  "msg_id": "server-message-uuid",
  "req_id": "client-request-uuid",
  "seq": 1,
  "event": "health",
  "recipient": "websocket",
  "recipient_id": "specific-channel-name",
  "payload": {
    "status": "ok"
  }
}
```

`msg_id` is generated by the backend for every outgoing message. `seq` is the backend-assigned event sequence number.

`recipient` identifies the recipient type. `recipient_id` identifies the concrete object or connection that the resolver must translate into WebSocket identifiers.

## Registries

The WebSocket layer uses metaclass-based registries:

- `ActionRegistryMeta` for client actions
- `EventRegistryMeta` for events sent to clients
- `RecipientRegistryMeta` for mapping recipients to WebSocket connections

Classes register themselves through the `name` argument passed to the metaclass:

```python
class Health(metaclass=ActionRegistryMeta, name="health"):
    ...
```

## Files

- [Actions](actions/README.md)
- [Events](events/README.md)
- [Recipients](recipients/README.md)
- [Errors](errors/README.md)
