from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PaymentTermConfig(models.Model):
    _name = "payment.term.config"
    _description = "Payment Term Config"

    name = fields.Char(string="Payment Term")
    payment_term_date = fields.Integer(string='Payment Term Days', default=0,)
    
    # ownership_contract_id = fields.Many2one(
    #     'ownership.contract', 
    #     string='Ownership Contract', 
    #     required=True,
    #     default=lambda self: self.env['ownership.contract'].search([], limit=1)
    # )
    # load_line_rs_own_id = fields.Many2one(
    #     'loan.line.rs.own', 
    #     string='Installments', 
    #     required=True,
    #     # default=lambda self: self.env['loan.line.rs.own'].search([], limit=1)
    # )
    
    
    
    
