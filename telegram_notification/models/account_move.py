from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = ["account.move",] # "telegram.notification.mixin"

    def write(self, vals):
        track_payment_state = "payment_state" in vals
        res = super().write(vals)

        if track_payment_state:
            for move in self.filtered(lambda m: m.move_type in ("out_invoice", "in_invoice")):
                if move.payment_state == "paid":
                    self._telegram_send(
                        (
                            "<b>Invoice Paid</b>\n"
                            f"Invoice: {move.name or move.ref or 'N/A'}\n"
                            f"Partner: {move.partner_id.display_name}\n"
                            f"Amount: {move.currency_id.symbol or ''}{move.amount_total:,.2f}"
                        )
                    )
        return res

    @api.model
    def _cron_notify_payment_due(self):
        today = fields.Date.today()
        invoices = self.search(
            [
                ("move_type", "in", ["out_invoice", "in_invoice"]),
                ("state", "=", "posted"),
                ("invoice_date_due", "!=", False),
                ("invoice_date_due", "<=", today),
                ("payment_state", "in", ["not_paid", "partial"]),
            ],
            limit=50,
        )
        for inv in invoices:
            self._telegram_send(
                (
                    "<b>Payment Due</b>\n"
                    f"Invoice: {inv.name or inv.ref or 'N/A'}\n"
                    f"Partner: {inv.partner_id.display_name}\n"
                    f"Due Date: {inv.invoice_date_due}\n"
                    f"Residual: {inv.currency_id.symbol or ''}{inv.amount_residual:,.2f}"
                )
            )
