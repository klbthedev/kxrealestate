from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class InstallmentTemplate(models.Model):
    _name = "installment.template"
    _description = "Installment Template"
    _inherit = ['mail.thread']

    advance_payment = fields.Integer(string='Advance Payment %')
    annual_raise = fields.Integer(string='Annual Raise %')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    deducted_amount = fields.Boolean(string='Deducted from amount?')
    duration_year = fields.Integer(string='Year')
    month = fields.Integer(string='Month')
    name = fields.Char(string='Name', required=True)
    note = fields.Html(string='Note')
    repetition_rate = fields.Integer(string='Repetition Rate (month)', default=1)

    @api.constrains('month', 'duration_year')
    def _check_rule_duration_year_month(self):
        if not self.month and not self.duration_year:
            raise ValidationError(_('Please set template duration either by months or years!'))
