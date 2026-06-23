from odoo import fields, models


class SalespersonCommissionLine(models.Model):
    _name = 'salesperson.commission.line'
    _description = 'Salesperson Commission Line'
    _order = 'release_date desc, id desc'

    amount = fields.Float(string='Commission Amount', required=True)
    amount_base = fields.Float(string='Base Amount', required=True)
    commission_percent = fields.Float(string='Commission %', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    contract_id = fields.Many2one('ownership.contract', string='Ownership Contract', required=True, ondelete='cascade')
    installment_id = fields.Many2one('loan.line.rs.own', string='Installment')
    note = fields.Char(string='Note')
    payment_id = fields.Many2one('account.payment', string='Payment')
    release_date = fields.Date(default=fields.Date.context_today, required=True)
    state = fields.Selection(
        [('pending', 'Pending'), ('earned', 'Earned'), ('paid', 'Paid'), ('cancelled', 'Cancelled')],
        default='earned',
        required=True,
    )
    user_id = fields.Many2one('res.users', string='Salesperson', required=True)
