# Beeflow WebSocket: Odbiorcy

## Rola Odbiorcy

Resolver odbiorcy tłumaczy logicznego odbiorcę zdarzenia na konkretne identyfikatory WebSocket. Dzięki temu emitter nie zależy od modeli domenowych ani od sposobu wyszukiwania uczestników sesji.

## Kontrakt Klasy

Każdy odbiorca implementuje:

```python
async def resolve(self, recipient_id: str) -> tuple[str, ...]:
    ...
```

Metoda zwraca krotkę identyfikatorów WebSocket, które powinny otrzymać zdarzenie.

## Rejestracja

Odbiorca jest rejestrowany przez `RecipientRegistryMeta`:

```python
class SessionRecipient(metaclass=RecipientRegistryMeta, name="session"):
    ...
```

Wartość `name` odpowiada polu `recipient` w `WebSocketEventPayload`.

## Wbudowani Odbiorcy

### `websocket`

Bezpośrednie dostarczenie do jednego połączenia WebSocket.

`recipient_id` jest konkretnym identyfikatorem połączenia.
