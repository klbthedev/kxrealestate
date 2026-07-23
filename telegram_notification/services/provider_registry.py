from __future__ import annotations

from typing import Dict
from typing import Type

from .base_provider import BaseProvider
from .telegram_provider import TelegramProvider


class ProviderRegistry:
    """
    Registry responsible for resolving providers.

    Future providers can simply be registered using:

        ProviderRegistry.register(
            WhatsAppProvider.channel,
            WhatsAppProvider
        )

    without changing business logic.
    """

    _providers: Dict[str, Type[BaseProvider]] = {}

    @classmethod
    def register(
        cls,
        channel: str,
        provider: Type[BaseProvider],
    ) -> None:
        cls._providers[channel] = provider

    @classmethod
    def unregister(
        cls,
        channel: str,
    ) -> None:
        cls._providers.pop(channel, None)

    @classmethod
    def get_provider(
        cls,
        env,
        channel: str,
    ) -> BaseProvider:
        provider_class = cls._providers.get(channel)

        if not provider_class:
            raise ValueError(
                f"Notification provider '{channel}' is not registered."
            )

        return provider_class(env)

    @classmethod
    def available_channels(cls):
        return sorted(cls._providers.keys())


ProviderRegistry.register(
    TelegramProvider.channel,
    TelegramProvider,
)
