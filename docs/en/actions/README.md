# Beeflow WebSocket: Actions

## Action Role

An action represents a message received from the client. An action does not return a ready HTTP response and does not send data directly through WebSocket. It executes logic and emits events with `yield`.

One action can emit zero, one, or many events.

## Class Contract

Every action implements:

```python
async def execute(
    self,
    message: WebSocketActionPayload,
    context: ActionContext,
) -> AsyncIterator[EventPluginProtocol]:
    ...
```

`message` contains the original action envelope sent by the client. `context` contains connection data that the client must not provide in the payload:

- `websocket_id`
- `user_id`

## Registration

An action is registered through `ActionRegistryMeta`:

```python
class CreateSession(metaclass=ActionRegistryMeta, name="CreateSession"):
    ...
```

The `CreateSession` name is the value of the `action` field in the client message.

## Built-in Actions

### `health`

Diagnostic action. Emits the `health` event directly to the current WebSocket connection.

Input payload:

```json
{
  "msg_id": "client-message-uuid",
  "req_id": "client-request-uuid",
  "action": "health",
  "payload": {}
}
```
