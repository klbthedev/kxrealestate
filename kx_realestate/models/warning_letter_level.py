from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ContractWarningLetter(models.Model):
    _name = "warning.letter.level"
    _description = "Warning Letter Levels"
    ###########################################################    
    name = fields.Char(string="Level Name")
    # avoid repeated warning letter level names
    _sql_constraints = [('unique_name','UNIQUE(name)','Warning Letter Level must be unique (No Repetition).')]
    
    
    
