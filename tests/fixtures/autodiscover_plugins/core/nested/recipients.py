"""Autodiscovered recipient fixtures."""

from beeflow_websocket.core.recipient_registry import RecipientRegistryMeta


class CoreAutodiscoveredRecipient(metaclass=RecipientRegistryMeta, name="core_autodiscovered_recipient"):
    """Recipient registered when its nested module is imported by autodiscovery."""

    async def resolve(self, recipient_id: str) -> tuple[str, ...]:
        """Return the fixture recipient unchanged."""
        return (recipient_id,)
