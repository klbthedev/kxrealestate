from odoo import fields, models

class BuildingType(models.Model):
    _name = "building.type"
    _description = "Building Type"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='Type')
