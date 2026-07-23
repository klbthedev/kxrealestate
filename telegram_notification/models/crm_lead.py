from odoo import models


class CrmLead(models.Model):
    _inherit = ["crm.lead",]# "telegram.notification.mixin"

    def write(self, vals):
        assigned = "user_id" in vals
        res = super().write(vals)
        if assigned:
            for lead in self.filtered(lambda l: l.user_id):
                self._telegram_send(
                    (
                        "<b>CRM Lead Assigned</b>\n"
                        f"Lead: {lead.name}\n"
                        f"Customer: {lead.partner_name or '-'}\n"
                        f"Assigned To: {lead.user_id.display_name}"
                    )
                )
        return res
