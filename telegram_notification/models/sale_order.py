from odoo import models


class SaleOrder(models.Model):
    _inherit = ["sale.order", ] #"telegram.notification.mixin"

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            self._telegram_send(
                (
                    "<b>Sale Order Confirmed</b>\n"
                    f"Order: {order.name}\n"
                    f"Customer: {order.partner_id.display_name}\n"
                    f"Total: {order.currency_id.symbol or ''}{order.amount_total:,.2f}"
                )
            )
        return res
