from odoo import fields, models
from odoo.tools.translate import _

class loan_line_rs(models.Model):
    _name = 'loan.line.rs'
    _order = 'serial'

    amount = fields.Float(string='Payment', digits=(16, 4))
    contract_partner_id = fields.Many2one(related='loan_id.partner_id', string="Partner")
    contract_building_id = fields.Many2one(related='loan_id.building_id', string="Building")
    contract_building_unit_id = fields.Many2one(related='loan_id.building_unit_id', string="Building Unit")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    date = fields.Date(string='Date')
    empty_col = fields.Char(readonly=True)
    loan_id = fields.Many2one('unit.reservation', ondelete='cascade', readonly=True)
    name = fields.Char(string='Name')
    paid = fields.Boolean(string='Paid')
    serial = fields.Integer(string='#')
