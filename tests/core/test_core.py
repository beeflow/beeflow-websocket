from collections.abc import AsyncIterator
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from uuid import UUID

from pydantic import ValidationError

from beeflow_websocket.core.action_registry import ActionContext, ActionPluginProtocol, ActionRegistryMeta
from beeflow_websocket.core.actions.health import Health
from beeflow_websocket.core.event_registry import EventPluginProtocol, EventRegistryMeta
from beeflow_websocket.core.events.health import HealthEvent
from beeflow_websocket.core.payloads import (
    ErrorPayload,
    WebSocketActionPayload,
    WebSocketEventPayload,
    WebSocketRequestIdentifier,
)
from beeflow_websocket.core.recipient_registry import RecipientPluginProtocol, RecipientRegistryMeta
from beeflow_websocket.core.recipients.websocket import WebSocketRecipient

CLIENT_MESSAGE_ID = UUID("11111111-1111-4111-8111-111111111111")
REQUEST_ID = UUID("22222222-2222-4222-8222-222222222222")
SERVER_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
FRAMEWORK_MARKERS = ("django", "channels", "fastapi")


class BeeflowWebsocketCoreArchitectureTests(TestCase):
    """Verify the framework-independent core package boundary."""

    def test_core_package_has_no_framework_imports(self) -> None:
        """Core communication modules stay independent from Django, Channels, and FastAPI."""
        core_path = Path(__file__).parents[2] / "src" / "beeflow_websocket" / "core"

        self.assertTrue(core_path.is_dir())
        for python_file in core_path.rglob("*.py"):
            source = python_file.read_text().lower()

            self.assertFalse(any(marker in source for marker in FRAMEWORK_MARKERS))


class BeeflowWebsocketProtocolTests(IsolatedAsyncioTestCase):
    """Verify runtime bodies of typing-only protocol contracts."""

    def test_action_protocol_has_no_runtime_default_behaviour(self) -> None:
        """Action protocol default body exists only as a static typing contract."""
        message = WebSocketActionPayload(msg_id=CLIENT_MESSAGE_ID, req_id=REQUEST_ID, action="health", payload={})
        context = ActionContext(websocket_id="test.websocket", user_id=1)

        self.assertIsNone(ActionPluginProtocol.execute(object(), message, context))

    async def test_async_protocols_have_no_runtime_default_behaviour(self) -> None:
        """Async protocol default bodies exist only as static typing contracts."""
        self.assertIsNone(await EventPluginProtocol.emit(object()))
        self.assertIsNone(await RecipientPluginProtocol.resolve(object(), "test.websocket"))


class RegistryMetaTests(TestCase):
    """Verify action, event, and recipient registry metaclass contracts."""

    def test_action_registry_uses_explicit_class_keyword_name(self) -> None:
        """Action classes can register under an explicit registry name."""

        class HealthCheck(metaclass=ActionRegistryMeta, name="health_check"):
            def execute(self) -> None: ...

        self.assertEqual(ActionRegistryMeta.REGISTRY["health_check"], HealthCheck)

    def test_action_registry_uses_plugin_name_attribute(self) -> None:
        """Action classes can register under their explicit plugin attribute."""

        class PluginNamedAction(metaclass=ActionRegistryMeta):
            __plugin_name__ = "plugin_named_action"

            def execute(self) -> None: ...

        self.assertEqual(ActionRegistryMeta.REGISTRY["plugin_named_action"], PluginNamedAction)

    def test_action_registry_can_skip_registration(self) -> None:
        """Action classes can opt out from registry insertion."""

        class HiddenAction(metaclass=ActionRegistryMeta):
            __register__ = False

            def execute(self) -> None: ...

        self.assertNotIn("HiddenAction", ActionRegistryMeta.REGISTRY)

    def test_event_registry_uses_explicit_class_keyword_name(self) -> None:
        """Event classes can register under an explicit registry name."""

        class HealthChecked(metaclass=EventRegistryMeta, name="health_checked"):
            def emit(self) -> None: ...

        self.assertEqual(EventRegistryMeta.REGISTRY["health_checked"], HealthChecked)

    def test_event_registry_uses_class_name_fallback(self) -> None:
        """Event classes can register under the class name fallback."""

        class ClassNamedEvent(metaclass=EventRegistryMeta):
            def emit(self) -> None: ...

        self.assertEqual(EventRegistryMeta.REGISTRY["ClassNamedEvent"], ClassNamedEvent)

    def test_event_registry_can_skip_registration(self) -> None:
        """Event classes can opt out from registry insertion."""

        class HiddenEvent(metaclass=EventRegistryMeta):
            __register__ = False

            def emit(self) -> None: ...

        self.assertNotIn("HiddenEvent", EventRegistryMeta.REGISTRY)

    def test_recipient_registry_uses_explicit_class_keyword_name(self) -> None:
        """Recipient classes can register under an explicit registry name."""

        class DirectRecipient(metaclass=RecipientRegistryMeta, name="direct"):
            async def resolve(self, recipient_id: str) -> tuple[str, ...]:
                return (recipient_id,)

        self.assertEqual(RecipientRegistryMeta.REGISTRY["direct"], DirectRecipient)

    def test_recipient_registry_uses_plugin_name_attribute(self) -> None:
        """Recipient classes can register under their explicit plugin attribute."""

        class PluginNamedRecipient(metaclass=RecipientRegistryMeta):
            __plugin_name__ = "plugin_named_recipient"

            async def resolve(self, recipient_id: str) -> tuple[str, ...]:
                return (recipient_id,)

        self.assertEqual(RecipientRegistryMeta.REGISTRY["plugin_named_recipient"], PluginNamedRecipient)

    def test_recipient_registry_can_skip_registration(self) -> None:
        """Recipient classes can opt out from registry insertion."""

        class HiddenRecipient(metaclass=RecipientRegistryMeta):
            __register__ = False

            async def resolve(self, recipient_id: str) -> tuple[str, ...]:
                return (recipient_id,)

        self.assertNotIn("HiddenRecipient", RecipientRegistryMeta.REGISTRY)

    def test_builtin_recipients_are_registered_as_classes(self) -> None:
        """Recipient registry resolves built-in recipient handlers through the recipient class registry."""
        self.assertEqual(RecipientRegistryMeta.REGISTRY["websocket"], WebSocketRecipient)


class ErrorPayloadTests(TestCase):
    """Verify RFC 9457 Problem Details payload contract."""

    def test_error_payload_returns_problem_details_response_body(self) -> None:
        """Error payload exposes standard problem details members and safe extensions."""
        payload = ErrorPayload(
            msg_id=SERVER_MESSAGE_ID,
            req_id=REQUEST_ID,
            type="https://beeflow.co.uk/problems/beeflow-websocket/unknown-action",
            title="Unknown WebSocket action",
            status=400,
            detail="The requested WebSocket action is not registered.",
            instance="/ws/",
            code="unknown_action",
        )

        self.assertEqual(ErrorPayload.media_type, "application/problem+json")
        self.assertEqual(
            payload.to_dict(),
            {
                "msg_id": str(SERVER_MESSAGE_ID),
                "req_id": str(REQUEST_ID),
                "type": "https://beeflow.co.uk/problems/beeflow-websocket/unknown-action",
                "title": "Unknown WebSocket action",
                "status": 400,
                "detail": "The requested WebSocket action is not registered.",
                "instance": "/ws/",
                "code": "unknown_action",
            },
        )

    def test_error_payload_omits_empty_optional_members(self) -> None:
        """Problem details response contains no empty optional members."""
        payload = ErrorPayload(
            type="about:blank",
            title="Bad Request",
            status=400,
            detail="The request cannot be processed.",
            code="bad_request",
            instance=None,
        )

        self.assertEqual(
            payload.to_dict(),
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "The request cannot be processed.",
                "code": "bad_request",
            },
        )

    def test_error_payload_rejects_incomplete_debug_information(self) -> None:
        """Problem details response requires useful debugging information."""
        with self.assertRaises(ValidationError):
            ErrorPayload(type=" ", title=" ", status=200, detail=" ", code=" ")

    def test_error_payload_requires_stable_error_code(self) -> None:
        """Problem details response always exposes a stable application error code."""
        with self.assertRaises(ValidationError):
            ErrorPayload(
                type="about:blank",
                title="Bad Request",
                status=400,
                detail="The request cannot be processed.",
            )


class ActionContextTests(TestCase):
    """Verify action dispatch context validation."""

    def test_action_context_rejects_blank_websocket_id(self) -> None:
        """Action context requires a concrete WebSocket connection identifier."""
        with self.assertRaises(ValidationError):
            ActionContext(websocket_id=" ", user_id=1)


class WebSocketEventPayloadTests(IsolatedAsyncioTestCase):
    """Verify the common WebSocket event payload contract."""

    def test_event_payload_returns_json_response_body(self) -> None:
        """Event payload exposes the stable event envelope sent to clients."""
        payload = WebSocketEventPayload(
            msg_id=SERVER_MESSAGE_ID,
            req_id=REQUEST_ID,
            seq=466,
            event="health",
            recipient="websocket",
            recipient_id="test.websocket",
            payload={"status": "ok"},
        )

        self.assertEqual(
            payload.to_dict(),
            {
                "msg_id": str(SERVER_MESSAGE_ID),
                "req_id": str(REQUEST_ID),
                "seq": 466,
                "event": "health",
                "recipient": "websocket",
                "recipient_id": "test.websocket",
                "payload": {"status": "ok"},
            },
        )

    def test_event_payload_rejects_blank_event_name(self) -> None:
        """Event payload requires a useful event name."""
        with self.assertRaises(ValidationError):
            WebSocketEventPayload(event=" ", recipient="websocket", recipient_id="test.websocket", payload={})

    def test_event_payload_accepts_explicit_empty_dispatch_metadata(self) -> None:
        """Event payload can be created before the transport adapter adds dispatch metadata."""
        payload = WebSocketEventPayload(
            msg_id=None,
            req_id=None,
            seq=None,
            event="health",
            recipient="websocket",
            recipient_id="test.websocket",
            payload={},
        )

        self.assertEqual(
            payload.to_dict(),
            {
                "event": "health",
                "recipient": "websocket",
                "recipient_id": "test.websocket",
                "payload": {},
            },
        )

    def test_event_payload_rejects_blank_recipient_id(self) -> None:
        """Event payload requires a useful recipient identifier."""
        with self.assertRaises(ValidationError):
            WebSocketEventPayload(event="health", recipient="websocket", recipient_id=" ", payload={})

    async def test_health_event_emits_pydantic_payload(self) -> None:
        """Events return the common Pydantic event payload."""
        payload = await HealthEvent(recipient="websocket", recipient_id="test.websocket", req_id=REQUEST_ID).emit()

        self.assertIsInstance(payload, WebSocketEventPayload)
        self.assertEqual(
            payload.to_dict(),
            {
                "req_id": str(REQUEST_ID),
                "event": "health",
                "recipient": "websocket",
                "recipient_id": "test.websocket",
                "payload": {"status": "ok"},
            },
        )


class WebSocketActionPayloadTests(TestCase):
    """Verify inbound WebSocket action envelope validation."""

    def test_action_payload_parses_message_and_request_identifiers_as_uuid(self) -> None:
        """Action payload uses UUID identifiers inside the backend contract."""
        payload = WebSocketActionPayload(
            msg_id=str(CLIENT_MESSAGE_ID),
            req_id=str(REQUEST_ID),
            action="health",
            payload={},
        )

        self.assertEqual(payload.msg_id, CLIENT_MESSAGE_ID)
        self.assertEqual(payload.req_id, REQUEST_ID)

    def test_action_payload_rejects_blank_text_members(self) -> None:
        """Action payload requires useful message, request, and action identifiers."""
        with self.assertRaises(ValidationError):
            WebSocketActionPayload(msg_id=CLIENT_MESSAGE_ID, req_id=REQUEST_ID, action=" ", payload={})

    def test_request_identifier_rejects_blank_request_id(self) -> None:
        """Request identifier extraction rejects blank request identifiers."""
        with self.assertRaises(ValidationError):
            WebSocketRequestIdentifier(req_id=" ")


class WebSocketRecipientTests(IsolatedAsyncioTestCase):
    """Verify framework-independent WebSocket recipient resolution."""

    async def test_websocket_recipient_resolves_direct_connection(self) -> None:
        """Direct WebSocket recipient returns the supplied channel name."""
        self.assertEqual(await WebSocketRecipient().resolve("test.websocket"), ("test.websocket",))


class ActionEmissionTests(IsolatedAsyncioTestCase):
    """Verify actions emit events instead of returning them."""

    async def test_health_action_yields_event(self) -> None:
        """Health action yields the event that should be emitted by the WebSocket emitter."""
        emitted_events = []
        message = WebSocketActionPayload(msg_id=CLIENT_MESSAGE_ID, req_id=REQUEST_ID, action="health", payload={})

        async for event in Health().execute(message, ActionContext(websocket_id="test.websocket", user_id=1)):
            emitted_events.append(event)

        self.assertEqual(len(emitted_events), 1)
        self.assertIsInstance(emitted_events[0], HealthEvent)

    async def test_health_action_uses_context_for_recipient(self) -> None:
        """Health action ignores client payload routing data and emits to the current WebSocket."""
        emitted_events = []
        message = WebSocketActionPayload(
            msg_id=CLIENT_MESSAGE_ID,
            req_id=REQUEST_ID,
            action="health",
            payload={"recipient": "websocket", "recipient_id": "other.websocket"},
        )

        async for event in Health().execute(message, ActionContext(websocket_id="test.websocket", user_id=1)):
            emitted_events.append(event)

        payload = await emitted_events[0].emit()

        self.assertEqual(payload.req_id, REQUEST_ID)
        self.assertEqual(payload.recipient, "websocket")
        self.assertEqual(payload.recipient_id, "test.websocket")
