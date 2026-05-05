"""Async WebSocket consumers for Beeflow WebSocket communication.

The consumer receives client action envelopes, validates only the transport-level message shape, dispatches
registered actions, and emits JSON events produced by those actions.
"""

from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from pydantic import ValidationError

from beeflow_websocket.core.action_registry import ActionContext, ActionPluginProtocol, ActionRegistryMeta
from beeflow_websocket.core.payloads import ErrorPayload, WebSocketActionPayload, WebSocketRequestIdentifier
from beeflow_websocket.core.problems import INVALID_MESSAGE_PROBLEM, UNKNOWN_ACTION_PROBLEM, build_problem_type
from beeflow_websocket.django.authentication import selected_authentication_subprotocol
from beeflow_websocket.django.emitters import WebSocketEventEmitter

INVALID_MESSAGE_DETAIL = (
    "Message must contain valid UUID 'msg_id' and 'req_id', a non-empty 'action' string, and an object 'payload'."
)
PROBLEM_TYPE_BASE_URL_SETTING = "BEEFLOW_WEBSOCKET_PROBLEM_TYPE_BASE_URL"


@runtime_checkable
class AuthenticatedWebSocketUserProtocol(Protocol):
    """Define the authenticated user fields required by the WebSocket consumer."""

    id: int
    is_authenticated: bool


def create_websocket_message_id() -> UUID:
    """Return a unique server-side WebSocket message identifier."""
    return uuid4()


class WebSocketConsumer(AsyncJsonWebsocketConsumer):
    """Handle one Beeflow WebSocket connection and dispatch action envelopes.

    Clients send objects validated by ``WebSocketActionPayload``. A valid envelope can still reference an unknown
    action; that case is reported as a WebSocket Problem Details payload instead of closing the connection.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Create a consumer with a per-connection event sequence counter."""
        super().__init__(*args, **kwargs)
        self.sequence = 0

    async def connect(self) -> None:
        """Open the Beeflow WebSocket connection for an authenticated user.

        The handshake only establishes the transport. Every client message is validated separately in
        ``receive_json`` so malformed payloads can be reported with the same Problem Details response shape.
        """
        if self._authenticated_user() is None:
            await self.close()
            return

        await self.accept(selected_authentication_subprotocol(self.scope))

    async def receive_json(self, content: object, **kwargs: object) -> None:
        """Validate one inbound JSON message and dispatch it as a client action.

        Invalid envelope shape is treated as a transport/API boundary error. Action-specific validation belongs to
        the action itself because only the action owns its payload contract.
        """
        req_id = self._extract_request_id(content)
        try:
            message = WebSocketActionPayload.model_validate(content)
            await self._dispatch_action(message)
        except ValidationError:
            await self._send_invalid_message_error(req_id)
            return

    async def _dispatch_action(self, message: WebSocketActionPayload) -> None:
        """Execute a registered action and emit every event yielded by that action.

        Actions are async generators because a single client action may produce zero, one, or many outbound events
        during one WebSocket exchange.
        """
        action_class = self._get_action_class(message.action)
        if action_class is None:
            # Unknown actions are handled here so every dispatch path emits the same client-visible error.
            await self._send_unknown_action_error(message.action, message.req_id)
            return

        emitter = WebSocketEventEmitter(
            channel_layer=self.channel_layer,
            message_id_factory=create_websocket_message_id,
            sequence_provider=self._next_sequence,
        )
        user = self._authenticated_user()
        if user is None:
            await self.close()
            return

        action_context = ActionContext(websocket_id=self.channel_name, user_id=user.id)

        async for event in action_class().execute(message, action_context):
            await emitter.emit(event)

    def _get_action_class(self, action_name: str) -> type[ActionPluginProtocol] | None:
        """Return the action class registered for the client action name.

        ``None`` is part of the dispatch contract so missing actions can be emitted as domain-level WebSocket errors.
        """
        return ActionRegistryMeta.REGISTRY.get(action_name)

    async def _send_invalid_message_error(self, req_id: UUID | None) -> None:
        """Emit a Problem Details response for an invalid WebSocket action envelope.

        This error means the consumer could not trust the message enough to resolve an action.
        """
        await self._send_problem(
            ErrorPayload(
                req_id=req_id,
                type=self._problem_type(INVALID_MESSAGE_PROBLEM),
                title="Invalid WebSocket message",
                status=400,
                detail=INVALID_MESSAGE_DETAIL,
                code="invalid_websocket_message",
                instance=self._connection_path(),
            )
        )

    async def _send_unknown_action_error(self, action_name: str, req_id: UUID) -> None:
        """Emit a Problem Details response for a valid envelope with an unregistered action name.

        This error means the envelope is valid, but the action registry has no matching action implementation.
        """
        await self._send_problem(
            ErrorPayload(
                req_id=req_id,
                type=self._problem_type(UNKNOWN_ACTION_PROBLEM),
                title="Unknown WebSocket action",
                status=400,
                detail=f"No WebSocket action is registered under '{action_name}'.",
                code="unknown_websocket_action",
                instance=self._connection_path(),
            )
        )

    async def _send_problem(self, payload: ErrorPayload) -> None:
        """Send a Problem Details payload through the WebSocket JSON channel.

        Problem payloads use the same JSON sender as events so clients receive one consistent WebSocket message shape.
        """
        await self.send_json(payload.with_message_id(create_websocket_message_id()).to_dict())

    async def beeflow_websocket_event(self, event: dict[str, object]) -> None:
        """Send a routed WebSocket event received from the channel layer to the connected client."""
        await self.send_json(event["payload"])

    def _connection_path(self) -> str:
        """Return the current WebSocket path used as the Problem Details instance URI."""
        return str(self.scope["path"])

    def _extract_request_id(self, content: object) -> UUID | None:
        """Return the request identifier from a raw message before full envelope validation."""
        try:
            return WebSocketRequestIdentifier.model_validate(content).req_id
        except ValidationError:
            return None

    def _problem_type(self, problem_slug: str) -> str:
        """Return the Problem Details type URI configured by the Django project."""
        problem_type_base_url = getattr(settings, PROBLEM_TYPE_BASE_URL_SETTING, None)

        return build_problem_type(problem_type_base_url, problem_slug)

    def _authenticated_user(self) -> AuthenticatedWebSocketUserProtocol | None:
        """Return the authenticated ASGI user required for action dispatch."""
        user = self.scope.get("user")
        if isinstance(user, AuthenticatedWebSocketUserProtocol) and user.is_authenticated:
            return user

        return None

    def _next_sequence(self) -> int:
        """Return the next per-connection outbound event sequence number."""
        self.sequence += 1

        return self.sequence
