from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ContractWarningLetter(models.Model):
    _name = "warning.letter"
    _description = "Contract Warning Letter"
    ###########################################################    
    ownership_contract_id = fields.Many2one(
        'ownership.contract', 
        string='Ownership Contract', 
        required=True,
        default=lambda self: self.env['ownership.contract'].search([], limit=1)
    )
    # warning_letter_level = fields.Selection([
    #     ('first','First'), 
    #     ('second','Second'), 
    #     ('third', 'Third'), 
    #     ('final', 'Final')], 
    #     string="Letter Level")
    letter_level_id = fields.Many2one(
        'warning.letter.level', 
        string='Letter Level', 
        required=True,
        default=lambda self: self.env['warning.letter.level'].search([], limit=1)
    )
    warning_letter_date = fields.Date(string='Letter Date')
    warning_letter_remark = fields.Char(string='Remark')
    warning_letter_file = fields.Binary('Upload File')
    
    
    
    
