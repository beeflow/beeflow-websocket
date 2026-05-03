# Beeflow WebSocket: Błędy

## Format

Błędy wysyłane przez WebSocket używają `ErrorPayload`, zgodnego z Problem Details RFC 9457.

Przykładowy payload:

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

Jeżeli wiadomość wejściowa zawiera poprawne `req_id`, błąd zwraca to samo `req_id`. Gdy `req_id` nie istnieje albo
jest puste, błąd nie może zostać skorelowany z żądaniem.

Backend generuje nowe `msg_id` dla każdego błędu. Błędy nie mają `seq`.

## Aktualne Błędy

### `invalid_websocket_message`

Emitowany, gdy wiadomość od klienta nie ma poprawnej koperty `WebSocketActionPayload`.

Jeżeli wiadomość zawiera poprawne `req_id`, odpowiedź błędu zwraca to samo `req_id`.
Jeżeli `req_id` jest puste albo go nie ma, błąd nie zawiera `req_id`.

Problem URL:

```text
https://beeflow.co.uk/problems/beeflow-websocket/invalid-message
```

### `unknown_websocket_action`

Emitowany, gdy koperta jest poprawna, ale `ActionRegistryMeta` nie ma klasy zarejestrowanej pod wskazaną nazwą akcji.

Ten błąd zawsze zwraca `req_id`, ponieważ powstaje po poprawnej walidacji koperty akcji.

Problem URL:

```text
https://beeflow.co.uk/problems/beeflow-websocket/unknown-action
```
