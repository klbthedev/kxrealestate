from odoo import fields, models

class BuildingDescription(models.Model):
    _name = "building.description"
    _description = "Building Description"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='State')
