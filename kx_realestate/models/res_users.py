from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    realestate_commission_percent = fields.Float(string='Real Estate Commission %', default=0.0)
    realestate_commission_release_policy = fields.Selection(
        [('on_payment', 'On Payment'), ('on_confirm', 'On Contract Confirmation')],
        default='on_payment',
        string='Real Estate Commission Policy',
    )
