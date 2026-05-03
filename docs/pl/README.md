# Beeflow WebSocket

## Cel

`beeflow_websocket` jest biblioteką do obsługi komunikacji WebSocket opartej o akcje i zdarzenia. Przyjmuje akcje od klienta, przekazuje je do zarejestrowanych klas akcji, a następnie wysyła zdarzenia emitowane przez te akcje.

Wbudowana ścieżka adaptera Django Channels to:

```text
ws/
```

Domyślny consumer Django przyjmuje połączenia tylko dla zalogowanych użytkowników.

## Przepływ

1. Klient otwiera połączenie WebSocket.
2. Klient wysyła akcję w kopercie `WebSocketActionPayload`.
3. Consumer znajduje klasę akcji w `ActionRegistryMeta`.
4. Akcja wykonuje logikę i emituje zero, jedno albo wiele zdarzeń przez `yield`.
5. `WebSocketEventEmitter` serializuje zdarzenie do `WebSocketEventPayload`.
6. Emitter znajduje resolver odbiorcy w `RecipientRegistryMeta`.
7. Resolver zwraca konkretne identyfikatory WebSocket.
8. Emitter wysyła JSON do wskazanych połączeń.

## Wewnętrzny Podział

Warstwa komunikacji jest podzielona na rdzeń i opcjonalne adaptery frameworków:

```text
beeflow_websocket/
  core/
  django/
  fastapi/
  flask/
```

`core` zawiera elementy niezależne od frameworka:

- payloady Pydantic
- rejestry akcji, zdarzeń i odbiorców
- kontrakt `ActionContext`
- kontrakty akcji, zdarzeń i odbiorców
- wspólne akcje, zdarzenia i odbiorców niezależnych od transportu

`django` zawiera integrację z Django Channels:

- consumer WebSocket
- routing WebSocket
- emitter wysyłający zdarzenia przez Channel Layer
- generowanie backendowego `msg_id`
- licznik `seq` dla połączenia WebSocket

`fastapi` zawiera integrację z FastAPI:

- handler endpointu WebSocket
- helper konfiguracji aplikacji zapisujący ustawienia w `app.state`
- emitter wysyłający zdarzenia przez bieżące połączenie WebSocket
- generowanie backendowego `msg_id`
- licznik `seq` dla połączenia WebSocket

Adapter FastAPI obsługuje bezpośrednie odpowiedzi na bieżącym połączeniu WebSocket. Broadcast między połączeniami
albo zewnętrzny pub/sub powinien być osobnym managerem połączeń.

`flask` zawiera integrację z Flask-Sock:

- handler endpointu WebSocket
- helper konfiguracji aplikacji zapisujący ustawienia w `app.config`
- emitter wysyłający zdarzenia przez bieżące połączenie WebSocket
- generowanie backendowego `msg_id`
- licznik `seq` dla połączenia WebSocket

Adapter Flask obsługuje bezpośrednie odpowiedzi na bieżącym połączeniu WebSocket. Broadcast między połączeniami albo
zewnętrzny pub/sub powinien być osobnym managerem połączeń.

Moduły w `core` nie importują Django, Channels, FastAPI ani Flask. Kod domenowy powinien importować kontrakty i rejestry z `beeflow_websocket.core`.
Kolejne adaptery powinny leżeć obok `django`, bez importowania kodu frameworków do `core`.

## Autodiscover Pluginów

Klasy akcji, zdarzeń i odbiorców rejestrują się w momencie importu modułu. Autodiscover importuje moduły pluginów z
aplikacji użytkownika podczas startu aplikacji, żeby mogły wykonać się metaklasy rejestrujące.

Autodiscover jest domyślnie włączony. Django przechodzi po każdej zainstalowanej aplikacji Django. FastAPI i Flask
sprawdzają pakiet, który wywołał `configure_beeflow_websocket`, oraz jego pakiety nadrzędne. Każdy adapter importuje te
konwencyjne moduły pluginów, gdy istnieją:

```text
my_app/actions.py
my_app/events.py
my_app/recipients.py
my_app/ws/actions.py
my_app/ws/events.py
my_app/ws/recipients.py
```

Brakujące moduły są pomijane. Błędy importu wewnątrz istniejących modułów nie są ukrywane.

Dla tego konwencyjnego układu FastAPI i Flask nie potrzebują konfiguracji autodiscover:

```python
configure_beeflow_websocket(
    app,
)
```

Ustaw `BEEFLOW_WEBSOCKET_AUTODISCOVER = False` w Django albo `autodiscover=False` w FastAPI i Flask, żeby wyłączyć
importy podczas startu.

## Zależności Runtime

Paczka trzyma integracje frameworków jako opcjonalne zależności:

| Instalacja | Instalowane przez tę paczkę | Nie jest instalowane | Kiedy doinstalować |
| --- | --- | --- | --- |
| `beeflow-websocket` | `pydantic` | Django, Channels, FastAPI, Flask, serwery WebSocket | Dodaj extra dla frameworka, jeśli projekt używa wspieranego adaptera. |
| `beeflow-websocket[django]` | `django`, `channels` | `daphne`, `channels-redis`, serwer Redis | Dodaj `daphne`, jeśli aplikacja ma obsługiwać Django Channels przez Daphne. Dodaj `channels-redis` i Redis, jeśli używasz Redis channel layer dla grup, wielu procesów workerów albo komunikacji między instancjami. |
| `beeflow-websocket[fastapi]` | `fastapi` | serwery ASGI, np. `uvicorn` albo `hypercorn`, zewnętrzny pub/sub, managery połączeń | Dodaj serwer ASGI, jeśli aplikacja jeszcze go nie zapewnia. Dodaj Redis albo inną warstwę pub/sub tylko wtedy, gdy broadcast ma działać między połączeniami, workerami albo instancjami. |
| `beeflow-websocket[flask]` | `flask`, `flask-sock` | serwery produkcyjne, np. `gunicorn`, zewnętrzny pub/sub, managery połączeń | Dodaj serwer produkcyjny używany przez deployment aplikacji. Dodaj Redis albo inną warstwę pub/sub tylko wtedy, gdy broadcast ma działać między połączeniami, workerami albo instancjami. |

## Kontrakt Wejściowy

Każda wiadomość przychodząca od klienta ma kształt:

```json
{
  "msg_id": "client-message-uuid",
  "req_id": "client-request-uuid",
  "action": "health",
  "payload": {}
}
```

`msg_id` identyfikuje pojedynczą wiadomość klienta. `req_id` identyfikuje żądanie klienta i musi zostać przepisane do zdarzeń oraz błędów wynikających z tego żądania. `action` wskazuje nazwę zarejestrowanej akcji. `payload` należy do konkretnej akcji.

## Spójność Komunikacji

`msg_id`, `req_id` i `seq` mają oddzielne role:

- `msg_id` od klienta identyfikuje pojedynczą wiadomość wejściową
- `msg_id` od backendu jest generowany osobno dla każdej wiadomości wychodzącej
- `req_id` koreluje żądanie klienta ze zdarzeniami i błędami wynikającymi z tego żądania
- `seq` jest nadawany przez backend dla zdarzeń wychodzących na danym połączeniu WebSocket

Zasady `req_id`:

1. poprawna akcja klienta musi mieć niepuste `req_id`
2. każde zdarzenie wynikające z tej akcji zwraca to samo `req_id`
3. każdy błąd wynikający z tej akcji zwraca to samo `req_id`
4. wiadomość bez poprawnego `req_id` jest błędna i nie jest przekazywana do akcji

`seq` jest dodawane przez `WebSocketEventEmitter`. Błędy `ErrorPayload` nie używają `seq`.

## Kontrakt Wyjściowy

Każde zdarzenie wysyłane do klienta ma kształt:

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

`msg_id` jest generowany przez backend dla każdej wiadomości wychodzącej. `seq` jest numerem kolejnym zdarzenia nadawanym przez backend.

`recipient` wskazuje typ odbiorcy. `recipient_id` wskazuje konkretny obiekt albo połączenie, które resolver ma zamienić na identyfikatory WebSocket.

## Rejestry

Warstwa WebSocket używa rejestrów opartych o metaklasy:

- `ActionRegistryMeta` dla akcji przychodzących od klienta
- `EventRegistryMeta` dla zdarzeń wysyłanych do klienta
- `RecipientRegistryMeta` dla mapowania odbiorców na połączenia WebSocket

Klasy rejestrują się przez argument `name` przekazany do metaklasy:

```python
class Health(metaclass=ActionRegistryMeta, name="health"):
    ...
```

## Pliki

- [Akcje](actions/README.md)
- [Zdarzenia](events/README.md)
- [Odbiorcy](recipients/README.md)
- [Błędy](errors/README.md)
