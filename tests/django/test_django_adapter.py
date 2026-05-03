from collections.abc import AsyncIterator
from importlib import import_module, reload
from uuid import UUID

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from beeflow_websocket.core.action_registry import ActionContext, ActionRegistryMeta
from beeflow_websocket.core.event_registry import EventRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import (
    WebSocketActionPayload,
    WebSocketEventPayload,
)
from beeflow_websocket.core.recipient_registry import (
    RecipientMapDoesNotExist,
)
from beeflow_websocket.django.consumer import WebSocketConsumer
from beeflow_websocket.django.emitters import WebSocketChannelLayerProtocol, WebSocketEventEmitter
from beeflow_websocket.django.routing import websocket_urlpatterns

TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CLIENT_MESSAGE_ID = UUID("11111111-1111-4111-8111-111111111111")
REQUEST_ID = UUID("22222222-2222-4222-8222-222222222222")
SERVER_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
INVALID_MESSAGE_DETAIL = (
    "Message must contain valid UUID 'msg_id' and 'req_id', a non-empty 'action' string, and an object 'payload'."
)


class MultipleHealthAction(metaclass=ActionRegistryMeta, name="multiple_health"):
    """Test action that emits more than one WebSocket event."""

    async def execute(self, message: WebSocketActionPayload, context: ActionContext) -> AsyncIterator[HealthEvent]:
        """Yield every event that should be emitted for one user action."""
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)
        yield HealthEvent(recipient="websocket", recipient_id=context.websocket_id, req_id=message.req_id)


class MissingRecipientEvent(metaclass=EventRegistryMeta, name="missing_recipient_event"):
    """Test event routed to an unregistered recipient type."""

    async def emit(self) -> WebSocketEventPayload:
        """Return an event payload with a recipient missing from the registry."""
        return WebSocketEventPayload(
            req_id=REQUEST_ID,
            event="missing_recipient_event",
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


class RecordingChannelLayer:
    """Record channel layer messages sent by the WebSocket event emitter."""

    def __init__(self) -> None:
        """Create an empty channel message recorder."""
        self.sent_messages: list[tuple[str, dict[str, object]]] = []

    async def send(self, channel: str, message: dict[str, object]) -> None:
        """Record one channel layer message."""
        self.sent_messages.append((channel, message))


class RecordingWebSocketSender:
    """Record channel layer messages sent by a WebSocket event emitter."""

    def __init__(self) -> None:
        """Create an empty channel layer recorder."""
        self.channel_layer = RecordingChannelLayer()


class RecordingWebSocketConsumer(WebSocketConsumer):
    """Record JSON payloads sent by the WebSocket consumer."""

    def __init__(self) -> None:
        """Create a consumer with enough WebSocket scope for direct dispatch tests."""
        super().__init__()
        self.scope = {"path": "/ws/"}
        self.channel_name = "test.websocket"
        self.sent_payloads: list[dict[str, object]] = []

    async def send_json(self, content: dict[str, object], close: bool = False) -> None:
        """Record the JSON payload passed by the consumer."""
        self.sent_payloads.append(content)


class AuthenticatedWebSocketUser:
    """Represent a logged-in ASGI user in WebSocket consumer tests."""

    id = 1
    is_authenticated = True


class AnonymousWebSocketUser:
    """Represent an anonymous ASGI user in WebSocket consumer tests."""

    is_authenticated = False


def authenticated_websocket_communicator() -> WebsocketCommunicator:
    """Create a WebSocket communicator with an authenticated user in ASGI scope."""
    communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/")
    communicator.scope["user"] = AuthenticatedWebSocketUser()

    return communicator


def anonymous_websocket_communicator() -> WebsocketCommunicator:
    """Create a WebSocket communicator with an anonymous user in ASGI scope."""
    communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), "/ws/")
    communicator.scope["user"] = AnonymousWebSocketUser()

    return communicator


class BeeflowWebsocketArchitectureTests(SimpleTestCase):
    """Verify the internal core and Django adapter separation."""

    def test_django_app_config_is_explicit(self) -> None:
        """Django app configuration points to the Beeflow WebSocket adapter."""
        app_module = reload(import_module("beeflow_websocket.django.apps"))

        self.assertEqual(app_module.BeeflowWebsocketDjangoConfig.name, "beeflow_websocket.django")
        self.assertEqual(app_module.BeeflowWebsocketDjangoConfig.label, "beeflow_websocket")
        self.assertEqual(
            app_module.BeeflowWebsocketDjangoConfig.default_auto_field,
            "django.db.models.BigAutoField",
        )

    def test_django_adapter_exposes_websocket_transport(self) -> None:
        """Django integration exposes the concrete Channels consumer and routing."""
        django_consumer = import_module("beeflow_websocket.django.consumer")
        django_routing = import_module("beeflow_websocket.django.routing")

        self.assertEqual(django_consumer.WebSocketConsumer, WebSocketConsumer)
        self.assertEqual(django_routing.websocket_urlpatterns, websocket_urlpatterns)


class BeeflowWebsocketDjangoProtocolTests(SimpleTestCase):
    """Verify runtime bodies of typing-only Django adapter protocol contracts."""

    async def test_channel_layer_protocol_has_no_runtime_default_behaviour(self) -> None:
        """Channel layer protocol default body exists only as a static typing contract."""
        self.assertIsNone(await WebSocketChannelLayerProtocol.send(object(), "test.websocket", {}))


class WebSocketEventEmitterTests(SimpleTestCase):
    """Verify WebSocket event emission."""

    async def test_emitter_sends_event_payload_json(self) -> None:
        """Emitter sends event payloads through recipients resolved by the recipient registry."""
        sender = RecordingWebSocketSender()

        await WebSocketEventEmitter(
            channel_layer=sender.channel_layer,
            message_id_factory=FixedMessageIdFactory(),
            sequence_provider=IncrementingSequenceProvider(),
        ).emit(HealthEvent(recipient="websocket", recipient_id="test.websocket", req_id=REQUEST_ID))

        self.assertEqual(
            sender.channel_layer.sent_messages,
            [
                (
                    "test.websocket",
                    {
                        "type": "beeflow.websocket.event",
                        "payload": {
                            "msg_id": str(SERVER_MESSAGE_ID),
                            "req_id": str(REQUEST_ID),
                            "seq": 1,
                            "event": "health",
                            "recipient": "websocket",
                            "recipient_id": "test.websocket",
                            "payload": {"status": "ok"},
                        },
                    },
                )
            ],
        )

    async def test_emitter_raises_when_recipient_is_not_registered(self) -> None:
        """Emitter fails loudly when no recipient resolver is registered for an event."""
        sender = RecordingWebSocketSender()

        with self.assertRaises(RecipientMapDoesNotExist):
            await WebSocketEventEmitter(
                channel_layer=sender.channel_layer,
                message_id_factory=FixedMessageIdFactory(),
                sequence_provider=IncrementingSequenceProvider(),
            ).emit(MissingRecipientEvent())


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class WebSocketConsumerTests(SimpleTestCase):
    """Verify clean async WebSocket consumer dispatch."""

    async def test_consumer_dispatches_registered_health_action(self) -> None:
        """Consumer dispatches an action and emits the yielded event payload."""
        communicator = authenticated_websocket_communicator()

        connected, _ = await communicator.connect()
        await communicator.send_json_to(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "action": "health", "payload": {}}
        )
        response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertTrue(connected)
        self.assertIsInstance(response["msg_id"], str)
        self.assertNotEqual(response["msg_id"], "")
        self.assertEqual(response["req_id"], str(REQUEST_ID))
        self.assertEqual(response["seq"], 1)
        self.assertIsInstance(response["recipient_id"], str)
        self.assertNotEqual(response["recipient_id"], "")
        self.assertEqual(
            {key: response[key] for key in ("event", "recipient", "payload")},
            {"event": "health", "recipient": "websocket", "payload": {"status": "ok"}},
        )

    async def test_consumer_emits_all_events_yielded_by_action(self) -> None:
        """One user action can emit multiple WebSocket events."""
        communicator = authenticated_websocket_communicator()

        connected, _ = await communicator.connect()
        await communicator.send_json_to(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "action": "multiple_health", "payload": {}}
        )
        first_response = await communicator.receive_json_from()
        second_response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertTrue(connected)
        self.assertEqual(first_response["req_id"], str(REQUEST_ID))
        self.assertEqual(second_response["req_id"], str(REQUEST_ID))
        self.assertEqual(first_response["seq"], 1)
        self.assertEqual(second_response["seq"], 2)
        self.assertEqual(first_response["recipient_id"], second_response["recipient_id"])
        self.assertEqual(
            {key: first_response[key] for key in ("event", "recipient", "payload")},
            {"event": "health", "recipient": "websocket", "payload": {"status": "ok"}},
        )
        self.assertEqual(
            {key: second_response[key] for key in ("event", "recipient", "payload")},
            {"event": "health", "recipient": "websocket", "payload": {"status": "ok"}},
        )

    async def test_consumer_returns_problem_details_for_unknown_action(self) -> None:
        """Unknown actions return a debuggable Problem Details payload."""
        communicator = authenticated_websocket_communicator()

        await communicator.connect()
        await communicator.send_json_to(
            {"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "action": "missing_action", "payload": {}}
        )
        response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertIsInstance(response["msg_id"], str)
        self.assertNotEqual(response["msg_id"], "")
        self.assertEqual(
            {key: response[key] for key in ("req_id", "type", "title", "status", "detail", "code", "instance")},
            {
                "req_id": str(REQUEST_ID),
                "type": "https://beeflow.co.uk/problems/beeflow-websocket/unknown-action",
                "title": "Unknown WebSocket action",
                "status": 400,
                "detail": "No WebSocket action is registered under 'missing_action'.",
                "code": "unknown_websocket_action",
                "instance": "/ws/",
            },
        )

    async def test_dispatch_action_emits_problem_details_for_unknown_action(self) -> None:
        """Action dispatch emits a debuggable Problem Details payload when no action exists."""
        consumer = RecordingWebSocketConsumer()
        message = WebSocketActionPayload(msg_id=CLIENT_MESSAGE_ID, req_id=REQUEST_ID, action="missing_action", payload={})

        await consumer._dispatch_action(message)

        self.assertEqual(len(consumer.sent_payloads), 1)
        self.assertIsInstance(consumer.sent_payloads[0]["msg_id"], str)
        self.assertNotEqual(consumer.sent_payloads[0]["msg_id"], "")
        self.assertEqual(
            {
                key: consumer.sent_payloads[0][key]
                for key in ("req_id", "type", "title", "status", "detail", "code", "instance")
            },
            {
                "req_id": str(REQUEST_ID),
                "type": "https://beeflow.co.uk/problems/beeflow-websocket/unknown-action",
                "title": "Unknown WebSocket action",
                "status": 400,
                "detail": "No WebSocket action is registered under 'missing_action'.",
                "code": "unknown_websocket_action",
                "instance": "/ws/",
            },
        )

    async def test_consumer_returns_request_id_for_invalid_message_when_available(self) -> None:
        """Invalid envelopes still return the client request identifier when it is present."""
        communicator = authenticated_websocket_communicator()

        await communicator.connect()
        await communicator.send_json_to({"msg_id": str(CLIENT_MESSAGE_ID), "req_id": str(REQUEST_ID), "payload": {}})
        response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertEqual(
            {key: response[key] for key in ("req_id", "type", "title", "status", "detail", "code", "instance")},
            {
                "req_id": str(REQUEST_ID),
                "type": "https://beeflow.co.uk/problems/beeflow-websocket/invalid-message",
                "title": "Invalid WebSocket message",
                "status": 400,
                "detail": INVALID_MESSAGE_DETAIL,
                "code": "invalid_websocket_message",
                "instance": "/ws/",
            },
        )

    async def test_consumer_returns_problem_details_without_request_id_when_request_id_is_missing(self) -> None:
        """Messages without a request identifier are invalid and cannot be correlated."""
        communicator = authenticated_websocket_communicator()

        await communicator.connect()
        await communicator.send_json_to({"payload": {}})
        response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertIsInstance(response["msg_id"], str)
        self.assertNotIn("req_id", response)
        self.assertEqual(
            {key: response[key] for key in ("type", "title", "status", "detail", "code", "instance")},
            {
                "type": "https://beeflow.co.uk/problems/beeflow-websocket/invalid-message",
                "title": "Invalid WebSocket message",
                "status": 400,
                "detail": INVALID_MESSAGE_DETAIL,
                "code": "invalid_websocket_message",
                "instance": "/ws/",
            },
        )

    async def test_consumer_sends_channel_layer_event_payload_to_client(self) -> None:
        """Consumer sends WebSocket event payloads received from the channel layer to the client."""
        consumer = RecordingWebSocketConsumer()

        await consumer.beeflow_websocket_event(
            {
                "type": "beeflow.websocket.event",
                "payload": {
                    "msg_id": str(SERVER_MESSAGE_ID),
                    "req_id": str(REQUEST_ID),
                    "seq": 1,
                    "event": "health",
                    "recipient": "websocket",
                    "recipient_id": "test.websocket",
                    "payload": {"status": "ok"},
                },
            }
        )

        self.assertEqual(
            consumer.sent_payloads,
            [
                {
                    "msg_id": str(SERVER_MESSAGE_ID),
                    "req_id": str(REQUEST_ID),
                    "seq": 1,
                    "event": "health",
                    "recipient": "websocket",
                    "recipient_id": "test.websocket",
                    "payload": {"status": "ok"},
                }
            ],
        )

    async def test_consumer_rejects_anonymous_websocket_connection(self) -> None:
        """Anonymous users cannot open the WebSocket connection."""
        communicator = anonymous_websocket_communicator()

        connected, _ = await communicator.connect()

        self.assertFalse(connected)

    def test_routing_uses_websocket_consumer(self) -> None:
        """WebSocket route uses the async consumer."""
        route = websocket_urlpatterns[0]

        self.assertEqual(str(route.pattern), "ws/")
        self.assertEqual(route.callback.consumer_class, WebSocketConsumer)
