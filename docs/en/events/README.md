# Beeflow WebSocket: Events

## Event Role

An event represents a message sent from the backend to the client. An event is created by an action, but it is sent only by `WebSocketEventEmitter`.

An event does not know Channel Layer details. It is responsible only for returning a consistent `WebSocketEventPayload` envelope.

## Class Contract

Every event implements:

```python
async def emit(self) -> WebSocketEventPayload:
    ...
```

The event class returns a base `WebSocketEventPayload` with these fields:

- `req_id`
- `event`
- `recipient`
- `recipient_id`
- `payload`

`msg_id` and `seq` are added later by the Django adapter, right before delivery through Channel Layer.

## Registration

An event is registered through `EventRegistryMeta`:

```python
class SessionCreatedEvent(metaclass=EventRegistryMeta, name="SessionCreated"):
    ...
```

## Built-in Events

### `health`

Confirms that the WebSocket dispatcher works.

Example payload:

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
