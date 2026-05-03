# Beeflow WebSocket: Zdarzenia

## Rola Zdarzenia

Zdarzenie reprezentuje wiadomość wysyłaną z backendu do klienta. Zdarzenie jest tworzone przez akcję, ale wysyła je wyłącznie `WebSocketEventEmitter`.

Zdarzenie nie zna szczegółów Channel Layer. Odpowiada tylko za zwrócenie spójnej koperty `WebSocketEventPayload`.

## Kontrakt Klasy

Każde zdarzenie implementuje:

```python
async def emit(self) -> WebSocketEventPayload:
    ...
```

Klasa zdarzenia zwraca bazowy `WebSocketEventPayload` z polami:

- `req_id`
- `event`
- `recipient`
- `recipient_id`
- `payload`

`msg_id` oraz `seq` są dodawane później przez adapter Django, tuż przed dostarczeniem wiadomości przez Channel Layer.

## Rejestracja

Zdarzenie jest rejestrowane przez `EventRegistryMeta`:

```python
class SessionCreatedEvent(metaclass=EventRegistryMeta, name="SessionCreated"):
    ...
```

## Wbudowane Zdarzenia

### `health`

Potwierdza, że dispatcher WebSocket działa.

Przykładowy payload:

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
