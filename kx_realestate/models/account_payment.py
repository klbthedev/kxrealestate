from odoo import fields, models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    loan_line_rs_own_id = fields.Many2one('loan.line.rs.own', string='Ownership Installment')
    loan_line_rs_rent_id = fields.Many2one('loan.line.rs.rent', string='Rental Contract Installment')
    real_estate_ref = fields.Char(string='Real Estate Ref')
    reservation_id =  fields.Many2one('unit.reservation', string='Reservation')
