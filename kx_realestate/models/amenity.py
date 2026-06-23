from odoo import fields, models


class RealEstateAmenity(models.Model):
    _name = "re.amenity"
    _description = "Real Estate Amenity"
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    active = fields.Boolean(default=True)
    code = fields.Char(string='Code', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    level = fields.Selection(
        [('building', 'Building'), ('unit', 'Unit'), ('both', 'Building and Unit')],
        default='both',
        required=True,
        tracking=True,
    )
    name = fields.Char(required=True, tracking=True)
    note = fields.Text(string='Description')
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('amenity_code_company_uniq', 'unique(code, company_id)', 'Amenity code must be unique per company.'),
    ]
