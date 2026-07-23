from odoo import api, models


class StockQuant(models.Model):
    _inherit = ["stock.quant",] # "telegram.notification.mixin"

    @api.model
    def _cron_notify_low_stock(self):
        threshold = float(
            self.env["ir.config_parameter"].sudo().get_param("tnc.low_stock_threshold", "5")
        )
        quants = self.search(
            [
                ("quantity", "<", threshold),
                ("location_id.usage", "=", "internal"),
            ],
            limit=50,
        )
        for quant in quants:
            self._telegram_send(
                (
                    "<b>Stock Low</b>\n"
                    f"Product: {quant.product_id.display_name}\n"
                    f"Location: {quant.location_id.display_name}\n"
                    f"On Hand: {quant.quantity:,.2f}\n"
                    f"Threshold: {threshold:,.2f}"
                )
            )
