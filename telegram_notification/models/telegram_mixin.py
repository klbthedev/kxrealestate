import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class TelegramNotificationMixin(models.AbstractModel):
    _name = "telegram.notification.mixin"
    _description = "Telegram Notification Mixin"

    @api.model
    def _is_telegram_enabled(self):
        return bool(self.env["ir.config_parameter"].sudo().get_param("tnc.telegram_enabled", False))

    @api.model
    def _telegram_send(self, message):
        icp = self.env["ir.config_parameter"].sudo()
        if not self._is_telegram_enabled():
            return False

        token = icp.get_param("tnc.telegram_bot_token")
        chat_id = icp.get_param("tnc.telegram_chat_id")

        if not token or not chat_id:
            _logger.warning("Telegram Notification Center is enabled but token/chat_id is missing.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(url, json=payload, timeout=8)
            response.raise_for_status()
            return True
        except Exception:
            _logger.exception("Failed to send telegram notification")
            return False
