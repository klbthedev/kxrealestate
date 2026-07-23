from __future__ import annotations

import logging
from typing import Any

import requests

from .base_provider import BaseProvider

_logger = logging.getLogger(__name__)


class TelegramProvider(BaseProvider):
    """
    Telegram Bot API implementation.
    """

    channel = "telegram"

    PARAM_TOKEN = "telegram_notification.bot_token"
    PARAM_TIMEOUT = "telegram_notification.timeout"

    def _config(self):
        icp = self.env["ir.config_parameter"].sudo()

        token = icp.get_param(
            self.PARAM_TOKEN,
            default="",
        )

        timeout = int(
            icp.get_param(
                self.PARAM_TIMEOUT,
                default="15",
            )
        )

        return token, timeout

    def send(
        self,
        recipient: Any,
        message: str,
        **kwargs,
    ) -> dict:
        """
        Send Telegram message.

        This method never raises exceptions to callers.
        """

        token, timeout = self._config()

        if not token:
            return {
                "success": False,
                "provider": self.channel,
                "message": message,
                "error": "Telegram Bot Token is not configured.",
                "response": None,
            }

        chat_id = getattr(recipient, "telegram_chat_id", False)

        if not chat_id:
            return {
                "success": False,
                "provider": self.channel,
                "message": message,
                "error": "Recipient has no Telegram Chat ID.",
                "response": None,
            }

        url = (
            f"https://api.telegram.org/"
            f"bot{token}/sendMessage"
        )

        payload = {
            "chat_id": chat_id,
            "text": message,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=timeout,
            )

            response.raise_for_status()

            data = response.json()

            if not data.get("ok"):

                error = data.get(
                    "description",
                    "Telegram API error.",
                )

                _logger.error(error)

                return {
                    "success": False,
                    "provider": self.channel,
                    "message": message,
                    "error": error,
                    "response": data,
                }

            return {
                "success": True,
                "provider": self.channel,
                "message": message,
                "error": None,
                "response": data,
            }

        except requests.exceptions.Timeout:

            _logger.exception(
                "Telegram request timeout."
            )

            return {
                "success": False,
                "provider": self.channel,
                "message": message,
                "error": "Connection timeout.",
                "response": None,
            }

        except requests.exceptions.RequestException as exc:

            _logger.exception(exc)

            return {
                "success": False,
                "provider": self.channel,
                "message": message,
                "error": str(exc),
                "response": None,
            }

        except Exception as exc:

            _logger.exception(exc)

            return {
                "success": False,
                "provider": self.channel,
                "message": message,
                "error": str(exc),
                "response": None,
            }