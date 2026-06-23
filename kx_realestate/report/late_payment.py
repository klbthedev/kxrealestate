from datetime import datetime
from odoo import api, models, _
from odoo.exceptions import UserError

class Parser(models.AbstractModel):
    _name = 'report.kx_realestate.report_late_payments_customers'

    def _get_lines(self, start_date, end_date, partner_ids):
        now = datetime.today().date()
        domain = [('date', '>=', start_date), ('date', '<=', end_date), ('date', '<', now), ('amount_residual', '>', 0)]
        if partner_ids:
            domain.append(('contract_partner_id', 'in', partner_ids))
        return self.env['loan.line.rs.own'].search(domain)

    def _get_total(self, start_date, end_date, partner_ids):
        return sum(self._get_lines(start_date, end_date, partner_ids).mapped('amount_residual'))

    @api.model
    def _get_report_values(self, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        due_payment = self.env['ir.actions.report']._get_report_from_name('kx_realestate.report_late_payments_customers')
        return {
            'doc_ids': self.ids,
            'doc_model': due_payment.model,
            'date_start':data['form']['date_start'],
            'date_end':data['form']['date_end'],
            'get_lines': self._get_lines(data['form']['date_start'],data['form']['date_end'],data['form']['partner_ids']),
            'get_total': self._get_total(data['form']['date_start'],data['form']['date_end'],data['form']['partner_ids']),
        }
