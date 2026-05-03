"""Flask WebSocket endpoint support for Beeflow WebSocket communication."""

import asyncio
import json
from uuid import UUID, uuid4

from flask import has_request_context, request
from pydantic import ValidationError

from beeflow_websocket.core.action_registry import ActionContext, ActionPluginProtocol, ActionRegistryMeta
from beeflow_websocket.core.payloads import ErrorPayload, WebSocketActionPayload, WebSocketRequestIdentifier
from beeflow_websocket.core.problems import INVALID_MESSAGE_PROBLEM, UNKNOWN_ACTION_PROBLEM, build_problem_type
from beeflow_websocket.flask.config import get_problem_type_base_url
from beeflow_websocket.flask.emitters import FlaskWebSocketEventEmitter, FlaskWebSocketProtocol, MessageIdFactory

INVALID_MESSAGE_DETAIL = (
    "Message must contain valid UUID 'msg_id' and 'req_id', a non-empty 'action' string, and an object 'payload'."
)


class FlaskWebSocketReceiveProtocol(FlaskWebSocketProtocol):
    """Define the Flask-Sock WebSocket receive contract required by the endpoint."""

    def receive(self, timeout: float | None = None) -> str | bytes | None: ...


def create_websocket_message_id() -> UUID:
    """Return a unique server-side WebSocket message identifier."""
    return uuid4()


class BeeflowWebSocketEndpoint:
    """Handle one Flask WebSocket connection and dispatch action envelopes.

    Flask authentication belongs to the route that creates this endpoint. The endpoint only needs the already-resolved
    user identifier for action context.
    """

    def __init__(
        self,
        websocket: FlaskWebSocketReceiveProtocol,
        user_id: int,
        *,
        websocket_id: str | None = None,
        message_id_factory: MessageIdFactory = create_websocket_message_id,
    ) -> None:
        """Create an endpoint for one WebSocket connection."""
        self.websocket = websocket
        self.user_id = user_id
        self.websocket_id = websocket_id or str(uuid4())
        self.message_id_factory = message_id_factory
        self.sequence = 0

    def run(self) -> None:
        """Receive and dispatch JSON messages until the client disconnects."""
        while True:
            content = self.websocket.receive()
            if content is None:
                return

            self.receive_json(content)

    def receive_json(self, content: str | bytes | object) -> None:
        """Validate one inbound JSON message and dispatch it as a client action."""
        decoded_content = self._decode_json(content)
        req_id = self._extract_request_id(decoded_content)
        try:
            message = WebSocketActionPayload.model_validate(decoded_content)
            asyncio.run(self._dispatch_action(message))
        except ValidationError:
            self._send_invalid_message_error(req_id)
            return

    async def _dispatch_action(self, message: WebSocketActionPayload) -> None:
        """Execute a registered action and emit every event yielded by that action."""
        action_class = self._get_action_class(message.action)
        if action_class is None:
            self._send_unknown_action_error(message.action, message.req_id)
            return

        emitter = FlaskWebSocketEventEmitter(
            websocket=self.websocket,
            websocket_id=self.websocket_id,
            message_id_factory=self.message_id_factory,
            sequence_provider=self._next_sequence,
        )
        action_context = ActionContext(websocket_id=self.websocket_id, user_id=self.user_id)

        async for event in action_class().execute(message, action_context):
            await emitter.emit(event)

    def _get_action_class(self, action_name: str) -> type[ActionPluginProtocol] | None:
        """Return the action class registered for the client action name."""
        return ActionRegistryMeta.REGISTRY.get(action_name)

    def _send_invalid_message_error(self, req_id: UUID | None) -> None:
        """Emit a Problem Details response for an invalid WebSocket action envelope."""
        self._send_problem(
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

    def _send_unknown_action_error(self, action_name: str, req_id: UUID) -> None:
        """Emit a Problem Details response for a valid envelope with an unregistered action name."""
        self._send_problem(
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

    def _send_problem(self, payload: ErrorPayload) -> None:
        """Send a Problem Details payload through the WebSocket JSON channel."""
        payload_with_message_id = payload.with_message_id(self.message_id_factory()).to_dict()

        self.websocket.send(json.dumps(payload_with_message_id))

    def _connection_path(self) -> str:
        """Return the current WebSocket path used as the Problem Details instance URI."""
        if has_request_context():
            return request.path

        return "/ws/"

    def _extract_request_id(self, content: object) -> UUID | None:
        """Return the request identifier from a raw message before full envelope validation."""
        try:
            return WebSocketRequestIdentifier.model_validate(content).req_id
        except ValidationError:
            return None

    def _problem_type(self, problem_slug: str) -> str:
        """Return the Problem Details type URI configured by the Flask app."""
        return build_problem_type(get_problem_type_base_url(), problem_slug)

    def _decode_json(self, content: str | bytes | object) -> object:
        """Return decoded JSON content when Flask-Sock gives the endpoint a text or bytes frame."""
        if isinstance(content, str | bytes | bytearray):
            try:
                return json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None

        return content

    def _next_sequence(self) -> int:
        """Return the next per-connection outbound event sequence number."""
        self.sequence += 1

        return self.sequence


def handle_beeflow_websocket(
    websocket: FlaskWebSocketReceiveProtocol,
    user_id: int,
    *,
    websocket_id: str | None = None,
) -> None:
    """Run the default Beeflow Flask WebSocket endpoint for one authenticated user."""
    BeeflowWebSocketEndpoint(
        websocket,
        user_id=user_id,
        websocket_id=websocket_id,
    ).run()
