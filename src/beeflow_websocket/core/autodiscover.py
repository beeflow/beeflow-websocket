"""Import configured plugin packages so registry metaclasses can run."""

from collections.abc import Iterable
from importlib import import_module
from importlib.util import find_spec
from inspect import currentframe
from pkgutil import walk_packages

DEFAULT_AUTODISCOVER_MODULES = (
    "actions",
    "events",
    "recipients",
    "ws.actions",
    "ws.events",
    "ws.recipients",
)


def normalize_autodiscover_packages(packages: Iterable[str] | str | None, *, setting_name: str) -> tuple[str, ...]:
    """Return validated package names configured for plugin autodiscovery."""
    if packages is None:
        return ()

    if isinstance(packages, str):
        raise TypeError(f"{setting_name} must be an iterable of package names, not a string.")

    normalized_packages: list[str] = []
    for package in packages:
        if not isinstance(package, str):
            raise TypeError(f"{setting_name} must contain only package name strings.")

        normalized_package = package.strip()
        if normalized_package == "":
            raise ValueError(f"{setting_name} must not contain blank package names.")

        normalized_packages.append(normalized_package)

    return tuple(normalized_packages)


def autodiscover_websocket_plugins(packages: Iterable[str] | str | None) -> tuple[str, ...]:
    """Import configured packages and their submodules recursively."""
    imported_modules: list[str] = []
    normalized_packages = normalize_autodiscover_packages(packages, setting_name="Autodiscover packages")

    for package_name in normalized_packages:
        imported_modules.extend(_import_package_tree(package_name))

    return tuple(imported_modules)


def autodiscover_available_websocket_plugins(packages: Iterable[str] | str | None) -> tuple[str, ...]:
    """Import configured packages that exist and skip absent optional package names."""
    imported_modules: list[str] = []
    normalized_packages = normalize_autodiscover_packages(packages, setting_name="Autodiscover packages")

    for package_name in normalized_packages:
        if _package_exists(package_name):
            imported_modules.extend(_import_package_tree(package_name))

    return tuple(imported_modules)


def build_autodiscover_package_names(
    base_packages: Iterable[str] | str | None,
    module_names: Iterable[str] | str | None = DEFAULT_AUTODISCOVER_MODULES,
) -> tuple[str, ...]:
    """Return absolute plugin package names from base package and conventional module names."""
    normalized_base_packages = normalize_autodiscover_packages(base_packages, setting_name="Autodiscover base packages")
    normalized_module_names = normalize_autodiscover_packages(module_names, setting_name="Autodiscover module names")
    package_names: list[str] = []

    for base_package in normalized_base_packages:
        for module_name in normalized_module_names:
            package_names.append(f"{base_package}.{module_name}")

    return tuple(package_names)


def get_module_base_packages(module_name: str | None) -> tuple[str, ...]:
    """Return candidate package names for the module configuring an adapter."""
    if module_name is None or module_name == "__main__":
        return ()

    parts = tuple(part for part in module_name.split(".") if part)
    if not parts:
        return ()

    return tuple(".".join(parts[:index]) for index in range(len(parts), 0, -1))


def get_calling_module_name(stack_depth: int) -> str | None:
    """Return the module name from a caller frame."""
    frame = currentframe()
    try:
        for _ in range(stack_depth):
            if frame is None:
                return None

            frame = frame.f_back

        if frame is None:
            return None

        module_name = frame.f_globals.get("__name__")
        if not isinstance(module_name, str) or module_name == "":
            return None

        return module_name
    finally:
        del frame


def _import_package_tree(package_name: str) -> list[str]:
    module = import_module(package_name)
    imported_modules = [module.__name__]
    package_paths = getattr(module, "__path__", None)
    if package_paths is None:
        return imported_modules

    for module_info in walk_packages(package_paths, f"{module.__name__}."):
        import_module(module_info.name)
        imported_modules.append(module_info.name)

    return imported_modules


def _package_exists(package_name: str) -> bool:
    try:
        return find_spec(package_name) is not None
    except ModuleNotFoundError:
        return False
