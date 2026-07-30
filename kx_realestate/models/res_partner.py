from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # is_tenant = fields.Boolean(string='Tenant')
    is_owner = fields.Boolean(string='Customer')
    is_vendor = fields.Boolean(string='Vendor')
    # ssn_id = fields.Char(string='ID')

    available_peppol_eas = fields.Char(string='Peppol EAS')
