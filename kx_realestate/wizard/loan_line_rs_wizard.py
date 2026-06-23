from odoo import fields, models

class LoanLineRsWizard(models.TransientModel):
    _name = 'loan.line.rs.wizard'

    amount = fields.Float(string='Payment', digits=(16, 4),)
    date = fields.Date(string='Date')
    discount_cash = fields.Float(string='Discount (Amt.) ')
    discount_percent = fields.Float(string='Discount %')
    # empty_col = fields.Char(readonly=True)
    empty_col = fields.Boolean()
    installment_line_id = fields.Integer('id')
    loan_id = fields.Many2one('customer.payment.check', ondelete='cascade', readonly=True)
    name = fields.Char(string='Name')
    serial = fields.Char('#')
    to_be_paid = fields.Boolean(string='Pay')

    def onchange_discount_cash(self, discount):
        if discount>0:
            return {'value': {'discount_percent':0.0}}

    def onchange_discount_percent(self, discount):
        if discount>0:
            return {'value': {'discount_cash':0.0}}
