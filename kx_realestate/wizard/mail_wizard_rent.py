from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _

class MailWizardRent(models.TransientModel):
    _name = 'mail.wizard.rent'

    def action_apply(self):
        loans = self.env['loan.line.rs.rent'].browse(self.env.context.get('active_ids', []))
        for loan in loans:
            if not loan.contract_partner_id.email:
                raise UserError(_('Please Provide Email for recepients!'))
            loan.send_multiple_installments_rent()
        return True
