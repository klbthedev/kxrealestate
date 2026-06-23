from odoo import api, models, _
from odoo.exceptions import UserError


class ReportDuePaymentsCustomersRent(models.AbstractModel):
    _name = 'report.kx_realestate.report_due_payments_customers_rent'

    def _get_lines(self, start_date, end_date, partner_ids):
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('amount_residual', '>', 0),
        ]
        if partner_ids:
            domain.append(('contract_partner_id', 'in', partner_ids))
        return self.env['loan.line.rs.rent'].search(domain)

    def _get_total(self, start_date, end_date, partner_ids):
        return sum(self._get_lines(start_date, end_date, partner_ids).mapped('amount_residual'))

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        report = self.env['ir.actions.report']._get_report_from_name(
            'kx_realestate.report_due_payments_customers_rent'
        )
        form = data['form']
        return {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'date_start': form['date_start'],
            'date_end': form['date_end'],
            'get_lines': self._get_lines(form['date_start'], form['date_end'], form['partner_ids']),
            'get_total': self._get_total(form['date_start'], form['date_end'], form['partner_ids']),
        }
