from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """
    Base notification provider.

    Every provider should inherit from this class.
    """

    channel: str = ""

    def __init__(self, env):
        self.env = env

    @abstractmethod
    def send(
        self,
        recipient: Any,
        message: str,
        **kwargs,
    ) -> dict:
        """
        Send notification.

        Returns
        -------
        dict
        {
            success: bool,
            provider: str,
            message: str,
            error: str|None,
            response: dict|None
        }
        """
        raise NotImplementedError
