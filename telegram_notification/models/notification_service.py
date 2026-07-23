from __future__ import annotations

import logging
from typing import Any

from odoo import api, models

from ..services.provider_registry import ProviderRegistry

_logger = logging.getLogger(__name__)


class NotificationService(models.Model):
    _name = "notification.service"
    _description = "Notification Service"

    DEFAULT_CHANNEL = "telegram"

    @api.model
    def notify(
        self,
        partner,
        message: str,
        channel: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Send a notification to a single partner.

        Example
        -------
        self.env["notification.service"].notify(
            partner,
            "Task assigned."
        )
        """

        result = {
            "success": False,
            "channel": channel or self.DEFAULT_CHANNEL,
            "provider": None,
            "partner_id": False,
            "message": message,
            "error": None,
            "response": None,
        }

        try:
            partner = self._validate_partner(partner)

            result["partner_id"] = partner.id

            provider = self._resolve_provider(
                partner,
                channel or self.DEFAULT_CHANNEL,
            )

            result["provider"] = provider.channel

            provider_result = provider.send(
                partner,
                message,
                **kwargs,
            )

            result.update(provider_result)

            return result

        except Exception as exc:
            _logger.exception("Notification failure")

            result["error"] = str(exc)
            return result

    @api.model
    def notify_many(
        self,
        partners,
        message: str,
        channel: str | None = None,
        **kwargs,
    ) -> list[dict]:
        """
        Send the same notification to multiple partners.
        """

        results = []

        for partner in partners:
            results.append(
                self.notify(
                    partner,
                    message,
                    channel=channel,
                    **kwargs,
                )
            )

        return results

    def _validate_partner(self, partner):
        """
        Validate recipient.
        """

        if not partner:
            raise ValueError("Recipient is required.")

        if partner._name != "res.partner":
            raise ValueError(
                "Recipient must be a res.partner record."
            )

        if not partner.exists():
            raise ValueError(
                "Recipient does not exist."
            )

        if not partner.telegram_notifications_enabled:
            raise ValueError(
                "Telegram notifications are disabled."
            )

        if not partner.telegram_chat_id:
            raise ValueError(
                "Recipient has no Telegram Chat ID."
            )

        return partner

    def _resolve_provider(
        self,
        partner,
        channel: str,
    ):
        """
        Resolve provider from registry.
        """

        return ProviderRegistry.get_provider(
            self.env,
            channel,
        )