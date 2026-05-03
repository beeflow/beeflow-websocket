import asyncio
from collections.abc import AsyncIterator
from importlib import import_module
from uuid import UUID

from flask import Flask

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.event_registry import EventRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload, WebSocketEventPayload
from beeflow_websocket.core.recipient_registry import RecipientMapDoesNotExist
from beeflow_websocket.flask import BeeflowWebSocketEndpoint, configure_beeflow_websocket, handle_beeflow_websocket
from beeflow_websocket.flask.emitters import FlaskWebSocketEventEmitter

CLIENT_MESSAGE_ID = UUID("11111111-1111-4111-8111-111111111111")
REQUEST_ID = UUID("22222222-2222-4222-8222-222222222222")
SERVER_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
INVALID_MESSAGE_DETAIL = (
    "Message must contain valid UUID 'msg_id' and 'req_id', a non-empty 'action' string, and an object 'payload'."
)
PROBLEM_TYPE_BASE_URL = "https://example.com/problems/websocket"


class MultipleFlaskHealthAction(metaclass=ActionRegistryMeta, name="flask_multiple_health"):
    """Test action that emits more than one WebSocket event."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield every event that should be emitted for one user action."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)


class MissingRecipientEvent(metaclass=EventRegistryMeta, name="flask_missing_recipient_event"):
    """Test event routed to an unregistered recipient type."""

    async def emit(self) -> WebSocketEventPayload:
        """Return an event payload with a recipient missing from the registry."""
        return WebSocketEventPayload(
            req_id=REQUEST_ID,
            event="flask_missing_recipient_event",
            recipient="missing_recipient",
            recipient_id="missing-recipient-1",
            payload={},
        )


class FixedMessageIdFactory:
    """Return a deterministic server message identifier in emitter tests."""

    def __call__(self) -> UUID:
        """Return the configured server message identifier."""
        return SERVER_MESSAGE_ID


class IncrementingSequenceProvider:
    """Return deterministic sequence numbers in emitter tests."""

    def __init__(self) -> None:
        """Create the sequence provider starting before the first event."""
        self.sequence = 0

    def __call__(self) -> int:
        """Return the next sequence number."""
        self.sequence += 1

        return self.sequence


class RecordingWebSocket:
    """Record JSON payloads sent by the Flask adapter."""

    def __init__(self, received_messages: list[str] | None = None) -> None:
        """Create a WebSocket recorder with optional incoming messages."""
        self.received_messages = received_messages or []
        self.sent_messages: list[str] = []

    @property
    def sent_payloads(self) -> list[dict[str, object]]:
        """Return sent JSON payloads decoded as dictionaries."""
        import json

        return [json.loads(message) for message in self.sent_messages]

    def receive(self, timeout: float | None = None) -> str | None:
        """Return the next incoming WebSocket message."""
        if not self.received_messages:
            return None

        return self.received_messages.pop(0)

    def send(self, data: str) -> None:
        """Record one outgoing WebSocket message."""
        self.sent_messages.append(data)


def create_test_app() -> Flask:
    """Create a Flask app configured for Beeflow WebSocket tests."""
    app = Flask(__name__)
    configure_beeflow_websocket(app, problem_type_base_url=PROBLEM_TYPE_BASE_URL)

    return app


def create_endpoint(websocket: RecordingWebSocket) -> BeeflowWebSocketEndpoint:
    """Create a deterministic Flask WebSocket endpoint for tests."""
    return BeeflowWebSocketEndpoint(
        websocket,
        user_id=1,
        websocket_id="flask.websocket",
        message_id_factory=FixedMessageIdFactory(),
    )


def test_flask_adapter_exposes_websocket_transport() -> None:
    """Flask integration exposes the concrete endpoint and emitter."""
    flask_endpoint = import_module("beeflow_websocket.flask.endpoint")
    flask_emitters = import_module("beeflow_websocket.flask.emitters")

    assert flask_endpoint.BeeflowWebSocketEndpoint is BeeflowWebSocketEndpoint
    assert flask_emitters.FlaskWebSocketEventEmitter is FlaskWebSocketEventEmitter


def test_flask_endpoint_dispatches_registered_health_action() -> None:
    """Flask endpoint dispatches an action and sends the yielded event payload."""
    app = create_test_app()
    websocket = RecordingWebSocket()

    with app.test_request_context("/ws/"):
        create_endpoint(websocket).receive_json(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "action": "health", "payload": {}}
        )

    assert websocket.sent_payloads == [
        {
            "msg_id": str(SERVER_MESSAGE_ID),
            "req_id": str(REQUEST_ID),
            "seq": 1,
            "event": "health",
            "recipient": "websocket",
            "recipient_id": "flask.websocket",
            "payload": {"status": "ok"},
        }
    ]


def test_flask_endpoint_emits_all_events_yielded_by_action() -> None:
    """One user action can emit multiple Flask WebSocket events."""
    app = create_test_app()
    websocket = RecordingWebSocket()

    with app.test_request_context("/ws/"):
        create_endpoint(websocket).receive_json(
            {
                "msg_id": str(CLIENT_MESSAGE_ID),
                "req_id": str(REQUEST_ID),
                "action": "flask_multiple_health",
                "payload": {},
            }
        )

    assert [payload["seq"] for payload in websocket.sent_payloads] == [1, 2]
    assert [payload["req_id"] for payload in websocket.sent_payloads] == [str(REQUEST_ID), str(REQUEST_ID)]
    assert [
        {key: payload[key] for key in ("event", "recipient", "payload")} for payload in websocket.sent_payloads
    ] == [
        {"event": "health", "recipient": "websocket", "payload": {"status": "ok"}},
        {"event": "health", "recipient": "websocket", "payload": {"status": "ok"}},
    ]


def test_flask_endpoint_returns_problem_details_for_unknown_action() -> None:
    """Unknown actions return a debuggable Problem Details payload."""
    app = create_test_app()
    websocket = RecordingWebSocket()

    with app.test_request_context("/ws/"):
        create_endpoint(websocket).receive_json(
            {
                "msg_id": str(CLIENT_MESSAGE_ID),
                "req_id": str(REQUEST_ID),
                "action": "missing_action",
                "payload": {},
            }
        )

    response = websocket.sent_payloads[0]

    assert {key: response[key] for key in ("msg_id", "req_id", "type", "title", "status", "detail", "code")} == {
        "msg_id": str(SERVER_MESSAGE_ID),
        "req_id": str(REQUEST_ID),
        "type": f"{PROBLEM_TYPE_BASE_URL}/unknown-action",
        "title": "Unknown WebSocket action",
        "status": 400,
        "detail": "No WebSocket action is registered under 'missing_action'.",
        "code": "unknown_websocket_action",
    }
    assert response["instance"] == "/ws/"


def test_flask_endpoint_returns_request_id_for_invalid_message_when_available() -> None:
    """Invalid envelopes still return the client request identifier when it is present."""
    app = create_test_app()
    websocket = RecordingWebSocket()

    with app.test_request_context("/ws/"):
        create_endpoint(websocket).receive_json(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "payload": {}}
        )

    response = websocket.sent_payloads[0]

    assert {key: response[key] for key in ("msg_id", "req_id", "type", "title", "status", "detail", "code")} == {
        "msg_id": str(SERVER_MESSAGE_ID),
        "req_id": str(REQUEST_ID),
        "type": f"{PROBLEM_TYPE_BASE_URL}/invalid-message",
        "title": "Invalid WebSocket message",
        "status": 400,
        "detail": INVALID_MESSAGE_DETAIL,
        "code": "invalid_websocket_message",
    }
    assert response["instance"] == "/ws/"


def test_flask_endpoint_defaults_problem_type_to_about_blank_without_configuration() -> None:
    """Flask endpoint uses about:blank when the app has no problem type base URL configured."""
    app = Flask(__name__)
    websocket = RecordingWebSocket()

    with app.test_request_context("/ws/"):
        create_endpoint(websocket).receive_json({"payload": {}})

    assert websocket.sent_payloads[0]["type"] == "about:blank"


def test_flask_handler_reads_json_messages_until_disconnect() -> None:
    """The default Flask handler reads text JSON messages from a Flask-Sock WebSocket."""
    app = create_test_app()
    websocket = RecordingWebSocket(
        [
            '{"msg_id": "11111111-1111-4111-8111-111111111111", '
            '"req_id": "22222222-2222-4222-8222-222222222222", '
            '"action": "health", "payload": {}}',
        ]
    )

    with app.test_request_context("/ws/"):
        handle_beeflow_websocket(websocket, user_id=1, websocket_id="flask.websocket")

    assert websocket.sent_payloads[0]["event"] == "health"


def test_flask_handler_returns_problem_details_for_invalid_json() -> None:
    """Invalid JSON text frames are reported as invalid WebSocket messages."""
    app = create_test_app()
    websocket = RecordingWebSocket(["{"])

    with app.test_request_context("/ws/"):
        handle_beeflow_websocket(websocket, user_id=1, websocket_id="flask.websocket")

    assert websocket.sent_payloads[0]["type"] == f"{PROBLEM_TYPE_BASE_URL}/invalid-message"


def test_flask_emitter_sends_event_payload_json() -> None:
    """Emitter sends event payloads through the current Flask WebSocket connection."""

    async def emit_event(websocket: RecordingWebSocket) -> None:
        await FlaskWebSocketEventEmitter(
            websocket=websocket,
            websocket_id="flask.websocket",
            message_id_factory=FixedMessageIdFactory(),
            sequence_provider=IncrementingSequenceProvider(),
        ).emit(HealthEvent(recipient="websocket", recipient_id="flask.websocket", req_id=REQUEST_ID))

    websocket = RecordingWebSocket()
    asyncio.run(emit_event(websocket))

    assert websocket.sent_payloads == [
        {
            "msg_id": str(SERVER_MESSAGE_ID),
            "req_id": str(REQUEST_ID),
            "seq": 1,
            "event": "health",
            "recipient": "websocket",
            "recipient_id": "flask.websocket",
            "payload": {"status": "ok"},
        }
    ]


def test_flask_emitter_raises_when_recipient_is_not_registered() -> None:
    """Emitter fails loudly when no recipient resolver is registered for an event."""

    async def emit_event(websocket: RecordingWebSocket) -> None:
        await FlaskWebSocketEventEmitter(
            websocket=websocket,
            websocket_id="flask.websocket",
            message_id_factory=FixedMessageIdFactory(),
            sequence_provider=IncrementingSequenceProvider(),
        ).emit(MissingRecipientEvent())

    websocket = RecordingWebSocket()
    try:
        asyncio.run(emit_event(websocket))
    except RecipientMapDoesNotExist:
        return

    raise AssertionError("RecipientMapDoesNotExist was not raised.")
