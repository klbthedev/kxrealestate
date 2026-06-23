from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', config_parameter='kx_real_estate.analytic_account_id')
    discount_account_id = fields.Many2one('account.account', string='Discount Account', config_parameter='kx_real_estate.discount_account_id')
    expense_account_id = fields.Many2one('account.account', string='Managerial Expenses Account', config_parameter='kx_real_estate.expense_account_id')
    account_id = fields.Many2one('account.account', string='Income Account', config_parameter='kx_real_estate.account_id')
    penalty_percent = fields.Integer(string='Penalty Percentage')
    penalty_account_id = fields.Many2one('account.account', string='Late Payments Penalty Account', config_parameter='kx_real_estate.penalty_account_id')
    reservation_hours = fields.Integer(string='Hours to release units reservation', config_parameter='kx_real_estate.reservation_hours')
    revenue_account_id = fields.Many2one('account.account', string='Revenue Account', config_parameter='kx_real_estate.revenue_account_id')
    security_deposit_account_id = fields.Many2one('account.account', string='Security Deposit Account', config_parameter='kx_real_estate.security_deposit_account_id')
