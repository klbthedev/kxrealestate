from odoo import fields, models

class LoanLineRsRentWizard(models.TransientModel):
    _name = 'loan.line.rs.rent.wizard'

    amount= fields.Float(string='Payment', digits=(16, 4))
    date= fields.Date(string='Date')
    discount_cash= fields.Float(string='Discount (Amt.)')
    discount_percent= fields.Float(string='Discount %')
    # empty_col= fields.Char(readonly=1)
    empty_col= fields.Boolean()
    loan_id= fields.Many2one('customer.rental.payment.check', ondelete='cascade', readonly=True)
    name= fields.Char(string='Name')
    loan_line_rs_rent_id = fields.Many2one('loan.line.rs.rent')
    serial= fields.Char('#')
    to_be_paid= fields.Boolean(string='Pay')

    def onchange_discount_cash(self, discount):
        if discount>0:
            return {'value': {'discount_percent':0.0}}

    def onchange_discount_percent(self, discount):
        if discount>0:
            return {'value': {'discount_cash':0.0}}
