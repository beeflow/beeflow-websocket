"""FastAPI WebSocket endpoint support for Beeflow WebSocket communication."""

from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from beeflow_websocket.core.action_registry import ActionContext, ActionPluginProtocol, ActionRegistryMeta
from beeflow_websocket.core.payloads import ErrorPayload, WebSocketActionPayload, WebSocketRequestIdentifier
from beeflow_websocket.core.problems import INVALID_MESSAGE_PROBLEM, UNKNOWN_ACTION_PROBLEM, build_problem_type
from beeflow_websocket.fastapi.config import get_problem_type_base_url
from beeflow_websocket.fastapi.emitters import FastAPIWebSocketEventEmitter, MessageIdFactory

INVALID_MESSAGE_DETAIL = (
    "Message must contain valid UUID 'msg_id' and 'req_id', a non-empty 'action' string, and an object 'payload'."
)


def create_websocket_message_id() -> UUID:
    """Return a unique server-side WebSocket message identifier."""
    return uuid4()


class BeeflowWebSocketEndpoint:
    """Handle one FastAPI WebSocket connection and dispatch action envelopes.

    FastAPI authentication belongs to the route or dependency that creates this endpoint. The endpoint only needs the
    already-resolved user identifier for action context.
    """

    def __init__(
        self,
        websocket: WebSocket,
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

    async def run(self) -> None:
        """Accept the connection and dispatch JSON messages until the client disconnects."""
        await self.websocket.accept()

        while True:
            try:
                content = await self.websocket.receive_json()
            except WebSocketDisconnect:
                return

            await self.receive_json(content)

    async def receive_json(self, content: object) -> None:
        """Validate one inbound JSON message and dispatch it as a client action."""
        req_id = self._extract_request_id(content)
        try:
            message = WebSocketActionPayload.model_validate(content)
            await self._dispatch_action(message)
        except ValidationError:
            await self._send_invalid_message_error(req_id)
            return

    async def _dispatch_action(self, message: WebSocketActionPayload) -> None:
        """Execute a registered action and emit every event yielded by that action."""
        action_class = self._get_action_class(message.action)
        if action_class is None:
            await self._send_unknown_action_error(message.action, message.req_id)
            return

        emitter = FastAPIWebSocketEventEmitter(
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

    async def _send_invalid_message_error(self, req_id: UUID | None) -> None:
        """Emit a Problem Details response for an invalid WebSocket action envelope."""
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
        """Emit a Problem Details response for a valid envelope with an unregistered action name."""
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
        """Send a Problem Details payload through the WebSocket JSON channel."""
        await self.websocket.send_json(payload.with_message_id(self.message_id_factory()).to_dict())

    def _connection_path(self) -> str:
        """Return the current WebSocket path used as the Problem Details instance URI."""
        return self.websocket.url.path

    def _extract_request_id(self, content: object) -> UUID | None:
        """Return the request identifier from a raw message before full envelope validation."""
        try:
            return WebSocketRequestIdentifier.model_validate(content).req_id
        except ValidationError:
            return None

    def _problem_type(self, problem_slug: str) -> str:
        """Return the Problem Details type URI configured by the FastAPI app."""
        return build_problem_type(get_problem_type_base_url(self.websocket), problem_slug)

    def _next_sequence(self) -> int:
        """Return the next per-connection outbound event sequence number."""
        self.sequence += 1

        return self.sequence


async def handle_beeflow_websocket(
    websocket: WebSocket,
    user_id: int,
    *,
    websocket_id: str | None = None,
) -> None:
    """Run the default Beeflow FastAPI WebSocket endpoint for one authenticated user."""
    await BeeflowWebSocketEndpoint(
        websocket,
        user_id=user_id,
        websocket_id=websocket_id,
    ).run()
