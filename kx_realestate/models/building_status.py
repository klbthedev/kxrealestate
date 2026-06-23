from odoo import fields, models

class BuildingStatus(models.Model):
    _name = "building.status"
    _description = "Building Status"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='State')
