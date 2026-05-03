"""WebSocket routing for Beeflow WebSocket communication."""

from django.urls import path

from beeflow_websocket.django.consumer import WebSocketConsumer

websocket_urlpatterns = [
    path("ws/", WebSocketConsumer.as_asgi()),  # type: ignore[arg-type]  # Channels routes ASGI apps here.
]
