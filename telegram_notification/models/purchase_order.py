from odoo import models


class PurchaseOrder(models.Model):
    _inherit = ["purchase.order",]#  "telegram.notification.mixin"

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            self._telegram_send(
                (
                    "<b>Purchase Order Confirmed</b>\n"
                    f"PO: {order.name}\n"
                    f"Vendor: {order.partner_id.display_name}\n"
                    f"Total: {order.currency_id.symbol or ''}{order.amount_total:,.2f}"
                )
            )
        return res
