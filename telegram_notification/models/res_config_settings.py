from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tnc_telegram_enabled = fields.Boolean(string="Enable Telegram Notifications")
    tnc_telegram_bot_token = fields.Char(string="Telegram Bot Token")
    tnc_telegram_chat_id = fields.Char(string="Telegram Chat ID")
    tnc_low_stock_threshold = fields.Float(string="Low Stock Threshold", default=5.0)

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("tnc.telegram_enabled", self.tnc_telegram_enabled)
        icp.set_param("tnc.telegram_bot_token", self.tnc_telegram_bot_token or "")
        icp.set_param("tnc.telegram_chat_id", self.tnc_telegram_chat_id or "")
        icp.set_param("tnc.low_stock_threshold", self.tnc_low_stock_threshold or 5.0)

    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            tnc_telegram_enabled=bool(icp.get_param("tnc.telegram_enabled", False)),
            tnc_telegram_bot_token=icp.get_param("tnc.telegram_bot_token", ""),
            tnc_telegram_chat_id=icp.get_param("tnc.telegram_chat_id", ""),
            tnc_low_stock_threshold=float(icp.get_param("tnc.low_stock_threshold", 5.0)),
        )
        return res
