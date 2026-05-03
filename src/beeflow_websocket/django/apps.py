"""Django application configuration for the Beeflow WebSocket adapter."""

from django.apps import AppConfig


class BeeflowWebsocketDjangoConfig(AppConfig):
    """Configure the optional Django integration app."""

    default_auto_field = "django.db.models.BigAutoField"
    label = "beeflow_websocket"
    name = "beeflow_websocket.django"

    def ready(self) -> None:
        """Import configured user plugin packages after Django apps are loaded."""
        from beeflow_websocket.django.autodiscover import autodiscover_websocket_plugins

        autodiscover_websocket_plugins()
