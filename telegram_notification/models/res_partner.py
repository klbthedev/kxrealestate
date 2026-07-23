from __future__ import annotations

from odoo import fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    telegram_chat_id = fields.Char(
        string="Telegram Chat ID",
        copy=False,
        tracking=True,
        help="Telegram chat identifier used by the notification service.",
    )

    telegram_notifications_enabled = fields.Boolean(
        string="Enable Telegram Notifications",
        default=True,
        tracking=True,
    )

    def send_telegram_notification(
        self,
        message: str,
    ) -> dict:
        """
        Convenience wrapper.

        Example
        -------
        partner.send_telegram_notification("Hello")
        """

        self.ensure_one()

        return self.env[
            "notification.service"
        ].notify(
            self,
            message,
        )
    
    
    def action_send_test_telegram_message(self):
        """Send a test Telegram notification."""
        self.ensure_one()

        result = self.env["notification.service"].notify(
            self,
            _("✅ Test message from Odoo.\n\nTelegram integration is configured correctly.")
        )

        if not result["success"]:
            raise UserError(result["error"])

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Telegram"),
                "message": _("Test message sent successfully."),
                "type": "success",
                "sticky": False,
            },
        }
    