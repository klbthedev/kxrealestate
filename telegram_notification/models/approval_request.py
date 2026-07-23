from odoo import api, models


class ApprovalRequest(models.Model):
    _inherit = ["approval.request",]# "telegram.notification.mixin"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for req in records:
            self._telegram_send(
                (
                    "<b>Approval Required</b>\n"
                    f"Request: {req.name}\n"
                    f"Category: {req.category_id.display_name}\n"
                    f"Requested By: {req.request_owner_id.display_name}"
                )
            )
        return records
