from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # is_tenant = fields.Boolean(string='Tenant')
    is_owner = fields.Boolean(string='Owner')
    # ssn_id = fields.Char(string='ID')
