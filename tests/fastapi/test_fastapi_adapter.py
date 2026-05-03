from collections.abc import AsyncIterator
from importlib import import_module
from uuid import UUID

import anyio
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.event_registry import EventRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import WebSocketActionPayload, WebSocketEventPayload
from beeflow_websocket.core.recipient_registry import RecipientMapDoesNotExist
from beeflow_websocket.fastapi import BeeflowWebSocketEndpoint, configure_beeflow_websocket, handle_beeflow_websocket
from beeflow_websocket.fastapi.emitters import FastAPIWebSocketEventEmitter

CLIENT_MESSAGE_ID = UUID("11111111-1111-4111-8111-111111111111")
REQUEST_ID = UUID("22222222-2222-4222-8222-222222222222")
SERVER_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
INVALID_MESSAGE_DETAIL = (
    "Message must contain valid UUID 'msg_id' and 'req_id', a non-empty 'action' string, and an object 'payload'."
)
PROBLEM_TYPE_BASE_URL = "https://example.com/problems/websocket"


class MultipleFastAPIHealthAction(metaclass=ActionRegistryMeta, name="fastapi_multiple_health"):
    """Test action that emits more than one WebSocket event."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield every event that should be emitted for one user action."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)


class MissingRecipientEvent(metaclass=EventRegistryMeta, name="fastapi_missing_recipient_event"):
    """Test event routed to an unregistered recipient type."""

    async def emit(self) -> WebSocketEventPayload:
        """Return an event payload with a recipient missing from the registry."""
        return WebSocketEventPayload(
            req_id=REQUEST_ID,
            event="fastapi_missing_recipient_event",
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
    """Record JSON payloads sent by the FastAPI event emitter."""

    def __init__(self) -> None:
        """Create an empty WebSocket send recorder."""
        self.sent_payloads: list[dict[str, object]] = []

    async def send_json(self, data: dict[str, object]) -> None:
        """Record one JSON payload."""
        self.sent_payloads.append(data)


def create_test_app() -> FastAPI:
    """Create a FastAPI app exposing the Beeflow WebSocket endpoint."""
    app = FastAPI()
    configure_beeflow_websocket(app, problem_type_base_url=PROBLEM_TYPE_BASE_URL)

    @app.websocket("/ws/")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await handle_beeflow_websocket(
            websocket,
            user_id=1,
            websocket_id="fastapi.websocket",
        )

    return app


def create_unconfigured_test_app() -> FastAPI:
    """Create a FastAPI app without a Problem Details type base URL configured."""
    app = FastAPI()

    @app.websocket("/ws/")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await handle_beeflow_websocket(websocket, user_id=1, websocket_id="fastapi.websocket")

    return app


def test_fastapi_adapter_exposes_websocket_transport() -> None:
    """FastAPI integration exposes the concrete endpoint and emitter."""
    fastapi_endpoint = import_module("beeflow_websocket.fastapi.endpoint")
    fastapi_emitters = import_module("beeflow_websocket.fastapi.emitters")

    assert fastapi_endpoint.BeeflowWebSocketEndpoint is BeeflowWebSocketEndpoint
    assert fastapi_emitters.FastAPIWebSocketEventEmitter is FastAPIWebSocketEventEmitter


def test_fastapi_endpoint_dispatches_registered_health_action() -> None:
    """FastAPI endpoint dispatches an action and sends the yielded event payload."""
    client = TestClient(create_test_app())

    with client.websocket_connect("/ws/") as websocket:
        websocket.send_json(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "action": "health", "payload": {}}
        )
        response = websocket.receive_json()

    assert isinstance(response["msg_id"], str)
    assert response["msg_id"] != ""
    assert response["req_id"] == str(REQUEST_ID)
    assert response["seq"] == 1
    assert response["recipient_id"] == "fastapi.websocket"
    assert {key: response[key] for key in ("event", "recipient", "payload")} == {
        "event": "health",
        "recipient": "websocket",
        "payload": {"status": "ok"},
    }


def test_fastapi_endpoint_emits_all_events_yielded_by_action() -> None:
    """One user action can emit multiple FastAPI WebSocket events."""
    client = TestClient(create_test_app())

    with client.websocket_connect("/ws/") as websocket:
        websocket.send_json(
            {
                "msg_id": str(CLIENT_MESSAGE_ID),
                "req_id": str(REQUEST_ID),
                "action": "fastapi_multiple_health",
                "payload": {},
            }
        )
        first_response = websocket.receive_json()
        second_response = websocket.receive_json()

    assert first_response["req_id"] == str(REQUEST_ID)
    assert second_response["req_id"] == str(REQUEST_ID)
    assert first_response["seq"] == 1
    assert second_response["seq"] == 2
    assert first_response["recipient_id"] == second_response["recipient_id"]
    assert {key: first_response[key] for key in ("event", "recipient", "payload")} == {
        "event": "health",
        "recipient": "websocket",
        "payload": {"status": "ok"},
    }
    assert {key: second_response[key] for key in ("event", "recipient", "payload")} == {
        "event": "health",
        "recipient": "websocket",
        "payload": {"status": "ok"},
    }


def test_fastapi_endpoint_returns_problem_details_for_unknown_action() -> None:
    """Unknown actions return a debuggable Problem Details payload."""
    client = TestClient(create_test_app())

    with client.websocket_connect("/ws/") as websocket:
        websocket.send_json(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "action": "missing_action", "payload": {}}
        )
        response = websocket.receive_json()

    assert isinstance(response["msg_id"], str)
    assert response["msg_id"] != ""
    assert {key: response[key] for key in ("req_id", "type", "title", "status", "detail", "code", "instance")} == {
        "req_id": str(REQUEST_ID),
        "type": f"{PROBLEM_TYPE_BASE_URL}/unknown-action",
        "title": "Unknown WebSocket action",
        "status": 400,
        "detail": "No WebSocket action is registered under 'missing_action'.",
        "code": "unknown_websocket_action",
        "instance": "/ws/",
    }


def test_fastapi_endpoint_returns_request_id_for_invalid_message_when_available() -> None:
    """Invalid envelopes still return the client request identifier when it is present."""
    client = TestClient(create_test_app())

    with client.websocket_connect("/ws/") as websocket:
        websocket.send_json({"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "payload": {}})
        response = websocket.receive_json()

    assert {key: response[key] for key in ("req_id", "type", "title", "status", "detail", "code", "instance")} == {
        "req_id": str(REQUEST_ID),
        "type": f"{PROBLEM_TYPE_BASE_URL}/invalid-message",
        "title": "Invalid WebSocket message",
        "status": 400,
        "detail": INVALID_MESSAGE_DETAIL,
        "code": "invalid_websocket_message",
        "instance": "/ws/",
    }


def test_fastapi_endpoint_returns_problem_details_without_request_id_when_request_id_is_missing() -> None:
    """Messages without a request identifier are invalid and cannot be correlated."""
    client = TestClient(create_test_app())

    with client.websocket_connect("/ws/") as websocket:
        websocket.send_json({"payload": {}})
        response = websocket.receive_json()

    assert isinstance(response["msg_id"], str)
    assert "req_id" not in response
    assert {key: response[key] for key in ("type", "title", "status", "detail", "code", "instance")} == {
        "type": f"{PROBLEM_TYPE_BASE_URL}/invalid-message",
        "title": "Invalid WebSocket message",
        "status": 400,
        "detail": INVALID_MESSAGE_DETAIL,
        "code": "invalid_websocket_message",
        "instance": "/ws/",
    }


def test_fastapi_endpoint_defaults_problem_type_to_about_blank_without_configuration() -> None:
    """FastAPI endpoint does not require Problem Details type configuration per endpoint."""
    client = TestClient(create_unconfigured_test_app())

    with client.websocket_connect("/ws/") as websocket:
        websocket.send_json({"payload": {}})
        response = websocket.receive_json()

    assert response["type"] == "about:blank"


def test_fastapi_emitter_sends_event_payload_json() -> None:
    """Emitter sends event payloads through the current FastAPI WebSocket connection."""

    async def emit_event(websocket: RecordingWebSocket) -> None:
        await FastAPIWebSocketEventEmitter(
            websocket=websocket,
            websocket_id="fastapi.websocket",
            message_id_factory=FixedMessageIdFactory(),
            sequence_provider=IncrementingSequenceProvider(),
        ).emit(HealthEvent(recipient="websocket", recipient_id="fastapi.websocket", req_id=REQUEST_ID))

    websocket = RecordingWebSocket()
    anyio.run(emit_event, websocket)
    assert websocket.sent_payloads == [
        {
            "msg_id": str(SERVER_MESSAGE_ID),
            "req_id": str(REQUEST_ID),
            "seq": 1,
            "event": "health",
            "recipient": "websocket",
            "recipient_id": "fastapi.websocket",
            "payload": {"status": "ok"},
        }
    ]


def test_fastapi_emitter_raises_when_recipient_is_not_registered() -> None:
    """Emitter fails loudly when no recipient resolver is registered for an event."""

    async def emit_event(websocket: RecordingWebSocket) -> None:
        await FastAPIWebSocketEventEmitter(
            websocket=websocket,
            websocket_id="fastapi.websocket",
            message_id_factory=FixedMessageIdFactory(),
            sequence_provider=IncrementingSequenceProvider(),
        ).emit(MissingRecipientEvent())

    websocket = RecordingWebSocket()
    try:
        anyio.run(emit_event, websocket)
    except RecipientMapDoesNotExist:
        return

    raise AssertionError("RecipientMapDoesNotExist was not raised.")
