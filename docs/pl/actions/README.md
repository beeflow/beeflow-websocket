# Beeflow WebSocket: Akcje

## Rola Akcji

Akcja reprezentuje wiadomość odebraną od klienta. Akcja nie zwraca gotowej odpowiedzi HTTP i nie wysyła danych bezpośrednio przez WebSocket. Wykonuje logikę i emituje zdarzenia przez `yield`.

Jedna akcja może wyemitować zero, jedno albo wiele zdarzeń.

## Kontrakt Klasy

Każda akcja implementuje:

```python
async def execute(
    self,
    message: WebSocketActionPayload,
    context: ActionContext,
) -> AsyncIterator[EventPluginProtocol]:
    ...
```

`message` zawiera oryginalną kopertę akcji wysłaną przez klienta. `context` zawiera dane połączenia, których klient nie może przekazać w payloadzie:

- `websocket_id`
- `user_id`

## Rejestracja

Akcja jest rejestrowana przez `ActionRegistryMeta`:

```python
class CreateSession(metaclass=ActionRegistryMeta, name="CreateSession"):
    ...
```

Nazwa `CreateSession` jest wartością pola `action` w wiadomości klienta.

## Wbudowane Akcje

### `health`

Akcja diagnostyczna. Emituje zdarzenie `health` bezpośrednio do aktualnego połączenia WebSocket.

Payload wejściowy:

```json
{
  "msg_id": "client-message-uuid",
  "req_id": "client-request-uuid",
  "action": "health",
  "payload": {}
}
```
