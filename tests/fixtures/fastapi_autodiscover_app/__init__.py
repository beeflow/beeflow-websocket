"""FastAPI app fixture for zero-config autodiscovery."""

from fastapi import FastAPI

from beeflow_websocket.fastapi import configure_beeflow_websocket


def create_app() -> FastAPI:
    """Create a FastAPI app that relies on conventional plugin autodiscovery."""
    app = FastAPI()
    configure_beeflow_websocket(app)

    return app
