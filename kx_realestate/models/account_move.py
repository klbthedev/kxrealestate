from odoo import fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    loan_line_rs_own_id = fields.Many2one('loan.line.rs.own', string='Ownership Installment')
    loan_line_rs_rent_id = fields.Many2one('loan.line.rs.rent', string='Rental Contract Installment')
    partner_id = fields.Many2one('res.partner', string="Owner")
    real_estate_ref = fields.Char(string='Real Estate Ref.')
    reservation_id =  fields.Many2one('unit.reservation', string='Reservation')
    ownership_id = fields.Many2one('ownership.contract', ondelete='cascade', readonly=True)
