from odoo import fields, models

class OwnerExpense(models.TransientModel):
    _name = 'owner.expense'

    amount= fields.Float(string='Amount', required=True)
    label= fields.Char(string='Label', required=True)
    main_id= fields.Many2one('owner.account.check', ondelete='cascade', readonly=True)
