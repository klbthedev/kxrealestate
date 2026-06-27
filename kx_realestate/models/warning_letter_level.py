from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ContractWarningLetter(models.Model):
    _name = "warning.letter.level"
    _description = "Warning Letter Levels"
    ###########################################################    
    name = fields.Char(string="Level Name")
    # avoid repeated warning letter level names
    _sql_constraints = [('unique_name','UNIQUE(name)','Warning Letter Level must be unique (No Repetition).')]
    ###########################################################
    # to avoid duplicate values due to case-sensitivity, normalize name values
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name'):
                vals['name'] = vals['name'].strip().title()
        return super().create(vals_list)
    ###########################################################
    def write(self, vals):
        if vals.get('name'):
            vals['name'] = vals['name'].strip().title()
        return super().write(vals)
    ###########################################################
    
