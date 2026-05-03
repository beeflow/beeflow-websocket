"""Flask app fixture for zero-config autodiscovery."""

from flask import Flask

from beeflow_websocket.flask import configure_beeflow_websocket


def create_app() -> Flask:
    """Create a Flask app that relies on conventional plugin autodiscovery."""
    app = Flask(__name__)
    configure_beeflow_websocket(app)

    return app
