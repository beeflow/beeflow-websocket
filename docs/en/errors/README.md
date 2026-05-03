# Beeflow WebSocket: Errors

## Format

Errors sent through WebSocket use `ErrorPayload`, which follows RFC 9457 Problem Details.

Example payload:

```json
{
  "msg_id": "server-message-uuid",
  "req_id": "client-request-uuid",
  "type": "https://beeflow.co.uk/problems/beeflow-websocket/unknown-action",
  "title": "Unknown WebSocket action",
  "status": 400,
  "detail": "No WebSocket action is registered under 'MissingAction'.",
  "code": "unknown_websocket_action",
  "instance": "/ws/"
}
```

If the incoming message contains a valid `req_id`, the error returns the same `req_id`. When `req_id` does not exist or
is blank, the error cannot be correlated with a request.

The backend generates a new `msg_id` for every error. Errors do not have `seq`.

## Current Errors

### `invalid_websocket_message`

Emitted when the client message does not have a valid `WebSocketActionPayload` envelope.

If the message contains a valid `req_id`, the error response returns the same `req_id`. If `req_id` is blank or missing,
the error does not contain `req_id`.

Problem URL:

```text
https://beeflow.co.uk/problems/beeflow-websocket/invalid-message
```

### `unknown_websocket_action`

Emitted when the envelope is valid, but `ActionRegistryMeta` has no class registered under the given action name.

This error always returns `req_id` because it is created after successful action envelope validation.

Problem URL:

```text
https://beeflow.co.uk/problems/beeflow-websocket/unknown-action
```
