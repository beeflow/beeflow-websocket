SECRET_KEY = "tests"  # nosec B105
INSTALLED_APPS = ["channels", "beeflow_websocket.django"]
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
