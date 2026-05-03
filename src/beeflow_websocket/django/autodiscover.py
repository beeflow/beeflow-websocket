"""Django settings integration for Beeflow WebSocket plugin autodiscovery."""

from collections.abc import Iterable

from django.apps import apps
from django.conf import settings

from beeflow_websocket.core.autodiscover import (
    DEFAULT_AUTODISCOVER_MODULES,
    autodiscover_available_websocket_plugins,
    autodiscover_websocket_plugins as autodiscover_configured_packages,
    build_autodiscover_package_names,
    normalize_autodiscover_packages,
)

AUTODISCOVER_SETTING = "BEEFLOW_WEBSOCKET_AUTODISCOVER"
AUTODISCOVER_MODULES_SETTING = "BEEFLOW_WEBSOCKET_AUTODISCOVER_MODULES"
AUTODISCOVER_PACKAGES_SETTING = "BEEFLOW_WEBSOCKET_AUTODISCOVER_PACKAGES"


def autodiscover_websocket_plugins() -> tuple[str, ...]:
    """Import user plugin packages from installed Django applications."""
    if not get_autodiscover_enabled():
        return ()

    discovered_modules = autodiscover_available_websocket_plugins(iter_installed_app_plugin_packages())
    configured_packages = autodiscover_configured_packages(get_autodiscover_packages())

    return discovered_modules + configured_packages


def get_autodiscover_enabled() -> bool:
    """Return whether Django startup should import configured plugin packages."""
    value = getattr(settings, AUTODISCOVER_SETTING, True)
    if not isinstance(value, bool):
        raise TypeError(f"{AUTODISCOVER_SETTING} must be a boolean.")

    return value


def get_autodiscover_modules() -> tuple[str, ...]:
    """Return validated app-relative plugin module names from Django settings."""
    value = getattr(settings, AUTODISCOVER_MODULES_SETTING, DEFAULT_AUTODISCOVER_MODULES)

    return normalize_autodiscover_packages(value, setting_name=AUTODISCOVER_MODULES_SETTING)


def get_autodiscover_packages() -> tuple[str, ...]:
    """Return validated extra absolute plugin package names from Django settings."""
    value = getattr(settings, AUTODISCOVER_PACKAGES_SETTING, ())

    return normalize_autodiscover_packages(value, setting_name=AUTODISCOVER_PACKAGES_SETTING)


def iter_installed_app_plugin_packages() -> Iterable[str]:
    """Yield conventional plugin module paths for every installed Django app."""
    app_names = (app_config.name for app_config in apps.get_app_configs())

    return build_autodiscover_package_names(app_names, get_autodiscover_modules())
