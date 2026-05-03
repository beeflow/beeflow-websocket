# Beeflow WebSocket: Recipients

## Recipient Role

A recipient resolver translates a logical event recipient into concrete WebSocket identifiers. This keeps the emitter independent from domain models and from the details of finding session participants.

## Class Contract

Every recipient implements:

```python
async def resolve(self, recipient_id: str) -> tuple[str, ...]:
    ...
```

The method returns a tuple of WebSocket identifiers that should receive the event.

## Registration

A recipient is registered through `RecipientRegistryMeta`:

```python
class SessionRecipient(metaclass=RecipientRegistryMeta, name="session"):
    ...
```

The `name` value matches the `recipient` field in `WebSocketEventPayload`.

## Built-in Recipients

### `websocket`

Direct delivery to one WebSocket connection.

`recipient_id` is the concrete connection identifier.
