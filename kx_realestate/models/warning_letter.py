from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ContractWarningLetter(models.Model):
    _name = "warning.letter"
    _description = "Contract Warning Letter"
    
    ###########################################################    
    
    ownership_contract_id = fields.Many2one('ownership.contract', string='', required=True, ondelete='cascade',)
    letter_level_id = fields.Many2one(
        'warning.letter.level', 
        string='Letter Level', 
        required=True,
        default=lambda self: self.env['warning.letter.level'].search([], limit=1)
    )
    warning_letter_date = fields.Date(string='Letter Date', required=True,)
    warning_letter_remark = fields.Char(string='Remark')
    warning_letter_file = fields.Binary('Upload File', required=True,)
    
    ###########################################################
    
    _sql_constraints = [(
        'unique_warning_letter_level_per_contract', 
        'UNIQUE(ownership_contract_id, letter_level_id)', 
        'Warning Letter Level must be unique within this contract.'
    )]
    
    ###########################################################
    
    
    
