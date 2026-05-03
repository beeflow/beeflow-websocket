"""FastAPI adapter namespace for Beeflow WebSocket communication."""

from beeflow_websocket.fastapi.config import configure_beeflow_websocket
from beeflow_websocket.fastapi.emitters import FastAPIWebSocketEventEmitter
from beeflow_websocket.fastapi.endpoint import BeeflowWebSocketEndpoint, handle_beeflow_websocket

__all__ = [
    "BeeflowWebSocketEndpoint",
    "FastAPIWebSocketEventEmitter",
    "configure_beeflow_websocket",
    "handle_beeflow_websocket",
]
