from odoo import fields, models, tools, api

# class LoanLineReport(models.Model):
#     # _name = "report.loan.line.rs.own"
#     _inherit = "loan.line.rs.own"
#     _description = "Loan Installments Analysis"
#     # _auto = False

#     name = fields.Char(readonly=True)
#     loan_id = fields.Many2one('ownership.contract', readonly=True)
#     partner_id = fields.Many2one('res.partner', readonly=True)

#     amount = fields.Float(string="Amount", readonly=True, group_operator="sum")
#     amount_paid = fields.Float(string="Amount Paid", readonly=True, group_operator="sum")
#     amount_remaining = fields.Float(string="Amount Remaining", readonly=True, group_operator="sum")

#     payment_state = fields.Selection([
#         ('paid', 'Paid'),
#         ('unpaid', 'Unpaid'),
#     ], readonly=True)

#     date = fields.Date(readonly=True)
#     installment_type = fields.Char(readonly=True)
#     column_label = fields.Char(string="Installment / Payment", readonly=True)

#     installment_count = fields.Integer(string="Installment Count", readonly=True)
#     installment_paid_count = fields.Integer(string="Paid Count", readonly=True)
#     installment_unpaid_count = fields.Integer(string="Unpaid Count", readonly=True)
#     installment_total_amount = fields.Float(string="Total Amount", readonly=True)
#     installment_paid_amount = fields.Float(string="Paid Amount", readonly=True)
#     installment_balance_amount = fields.Float(string="Remaining Amount", readonly=True)

#     def init(self):
#         tools.drop_view_if_exists(self._cr, 'report_loan_line_rs_own')
#         self._cr.execute("""
#             CREATE OR REPLACE VIEW report_loan_line_rs_own AS (
#                 SELECT
#                     MIN(lro.id) AS id,
#                     lro.loan_id AS loan_id,
#                     oc.partner_id AS partner_id,

#                     -- sums for measures
#                     SUM(lro.amount) AS amount,
#                     SUM(COALESCE(lro.total_paid_amount,0)) AS amount_paid,
#                     SUM(COALESCE(lro.total_remaining_amount,lro.amount)) AS amount_remaining,

#                     -- counts
#                     COUNT(lro.id) AS installment_count,
#                     COUNT(CASE WHEN COALESCE(lro.total_remaining_amount,lro.amount) <= 0 THEN 1 END) AS installment_paid_count,
#                     COUNT(CASE WHEN COALESCE(lro.total_remaining_amount,lro.amount) > 0 THEN 1 END) AS installment_unpaid_count

#                 FROM loan_line_rs_own lro
#                 LEFT JOIN ownership_contract oc ON oc.id = lro.loan_id

#                 GROUP BY lro.loan_id, oc.partner_id
#             )
#         """)
    # def init(self):
    #     tools.drop_view_if_exists(self._cr, 'report_loan_line_rs_own')
    #     self._cr.execute("""
    #         CREATE OR REPLACE VIEW report_loan_line_rs_own AS (
    #             SELECT
    #                 MIN(lro.id) AS id,
    #                 lro.name AS name,
    #                 lro.loan_id AS loan_id,
    #                 oc.partner_id AS partner_id,
    #                 lro.amount AS amount,
    #                 COALESCE(lro.total_paid_amount, 0) AS amount_paid,
    #                 COALESCE(lro.total_remaining_amount, lro.amount) AS amount_remaining,
    #                 CASE WHEN COALESCE(lro.total_remaining_amount, lro.amount) <= 0 THEN 'paid' ELSE 'unpaid' END AS payment_state,
    #                 lro.date AS date,
    #                 lro.name || ' (' || CASE WHEN COALESCE(lro.total_remaining_amount, lro.amount) <= 0 THEN 'paid' ELSE 'unpaid' END || ')' AS column_label,
    #                 COUNT(lro.id) AS installment_count,
    #                 COUNT(CASE WHEN COALESCE(lro.total_remaining_amount, lro.amount) <= 0 THEN 1 END) AS installment_paid_count,
    #                 COUNT(CASE WHEN COALESCE(lro.total_remaining_amount, lro.amount) > 0 THEN 1 END) AS installment_unpaid_count,
    #                 SUM(lro.amount) AS installment_total_amount,
    #                 SUM(COALESCE(lro.total_paid_amount, 0)) AS installment_paid_amount,
    #                 SUM(COALESCE(lro.total_remaining_amount, lro.amount)) AS installment_balance_amount
    #             FROM loan_line_rs_own lro
    #             LEFT JOIN ownership_contract oc ON oc.id = lro.loan_id
    #             GROUP BY
    #                 lro.loan_id,
    #                 lro.name,
    #                 lro.amount,
    #                 lro.total_paid_amount,
    #                 lro.total_remaining_amount,
    #                 lro.date,
    #                 oc.partner_id
    #         )
    #     """)


class ReportOwnershipContractBI(models.Model):
    _name = "report.ownership.contract.bi"
    _description = "Ownership Contracts Statistics"
    _auto = False
    _order = 'contract_date desc'

    # Contract Info
    name = fields.Char(string='Contract', readonly=True)
    contract_date = fields.Date(string='Contract Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsible', readonly=True)
    state = fields.Selection([('draft','Draft'),
                              ('confirmed','Confirmed'),
                              ('cancel','Canceled')], string='State', readonly=True)

    # Property Info
    site_id = fields.Many2one('re.site', string='Site', readonly=True)
    block_id = fields.Many2one('re.block', string='Block', readonly=True)
    floor_id = fields.Many2one('re.floor', string='Floor', readonly=True)
    contract_building_id = fields.Many2one('building.building', string='Property', readonly=True)
    product_template_id = fields.Many2one('product.template', string='Unit', readonly=True)

    # Invoice / Payment Info
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')], readonly=True)
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy')
    ], string='Payment State', readonly=True)
    due_date = fields.Date(string='Due Date', readonly=True)

    # Amounts / Balances
    amount = fields.Float(string='Amount', digits=(16, 4), readonly=True)
    paid = fields.Float(string='Paid Amount', readonly=True)
    unpaid = fields.Float(string='Balance', readonly=True)
    discount_total = fields.Float(string='Total Discount', readonly=True)

    # Installment Info
    installment_number = fields.Char(string='Installment Number', readonly=True)
    installment_name = fields.Char(string='Installment Name', readonly=True)
    loan_line_count = fields.Integer(string="Installments Count", readonly=True)
    installment_paid_count = fields.Integer(string="Paid Installments", readonly=True)
    installment_unpaid_count = fields.Integer(string="Unpaid Installments", readonly=True)
    installment_total_amount = fields.Float(string="Installment Total", readonly=True)
    installment_paid_amount = fields.Float(string="Installment Paid", readonly=True)
    installment_balance_amount = fields.Float(string="Installment Balance", readonly=True)
    
    # SUM versions for monetary analysis
    installment_paid_sum = fields.Float(string="Paid Amount Sum", readonly=True)
    installment_unpaid_sum = fields.Float(string="Unpaid Amount Sum", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_ownership_contract_bi')
        self._cr.execute("""
        CREATE OR REPLACE VIEW report_ownership_contract_bi AS (
            SELECT
                MIN(lro.id) AS id,
                oc.name,
                oc.date AS contract_date,
                oc.partner_id AS partner_id,
                oc.user_id AS user_id,
                oc.state AS state,
                oc.site_id AS site_id,
                oc.block_id AS block_id,
                oc.floor_id AS floor_id,
                oc.building_id AS contract_building_id,
                oc.building_unit_id AS product_template_id,
                lro.date AS due_date,
                lro.invoice_id AS invoice_id,
                am.state AS invoice_state,
                am.payment_state AS payment_state,
                lro.amount AS amount,
                (lro.amount - am.amount_residual) AS paid,
                am.amount_residual AS unpaid,
                lro.number AS installment_number,
                lro.name AS installment_name,
                COUNT(lro.id) AS loan_line_count,
                COUNT(CASE WHEN (lro.amount - am.amount_residual) <= 0 THEN 1 ELSE NULL END) AS installment_paid_count,
                COUNT(CASE WHEN (lro.amount - am.amount_residual) > 0 THEN 1 ELSE NULL END) AS installment_unpaid_count,
                SUM(lro.amount) AS installment_total_amount,
                SUM(lro.amount - am.amount_residual) AS installment_paid_amount,
                SUM(am.amount_residual) AS installment_balance_amount,
                SUM(CASE WHEN (lro.amount - am.amount_residual) <= 0 THEN lro.amount ELSE 0 END) AS installment_paid_sum,
                SUM(CASE WHEN (lro.amount - am.amount_residual) > 0 THEN lro.amount ELSE 0 END) AS installment_unpaid_sum,
                SUM(COALESCE(lro.original_amount,0) - lro.amount) AS discount_total
            FROM ownership_contract oc
            LEFT JOIN loan_line_rs_own lro ON oc.id = lro.loan_id
            LEFT JOIN account_move am ON am.id = lro.invoice_id
            GROUP BY
                oc.name, oc.date, oc.partner_id, oc.user_id, oc.state,
                oc.site_id, oc.block_id, oc.floor_id, oc.building_id, oc.building_unit_id,
                lro.date, lro.amount, lro.number, lro.name, lro.invoice_id,
                am.amount_residual, am.state, am.payment_state
        )
        """)

# class ReportOwnershipContractBI(models.Model):
#     _name = "report.ownership.contract.bi"
#     _description = "Ownership Contracts Statistics"
#     _auto = False
#     _order = 'contract_date desc'

#     amount = fields.Float(string='Amount', digits=(16, 4), readonly=True)
#     contract_date = fields.Date(string='Contract Date', readonly=True)
#     product_template_id = fields.Many2one('product.template', string='Unit', readonly=True)
#     contract_building_id = fields.Many2one('building.building', string='Property', readonly=True)
#     due_date = fields.Date(string='Due Date', readonly=True)
#     invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
#     invoice_state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')], readonly=True)
#     name = fields.Char(string='Contract', readonly=True)
#     paid = fields.Float(string='Paid Amount', readonly=True)
#     partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
#     payment_state = fields.Selection([('not_paid', 'Not Paid'),
#                                       ('in_payment', 'In Payment'),
#                                       ('paid', 'Paid'),
#                                       ('partial', 'Partially Paid'),
#                                       ('reversed', 'Reversed'),
#                                       ('invoicing_legacy', 'Invoicing App Legacy')], string='Payment State', readonly=True)
#     state = fields.Selection([('draft','Draft'),
#                              ('confirmed','Confirmed'),
#                              ('cancel','Canceled'),
#                              ], string='State')
#     unpaid = fields.Float(string='Balance', readonly=True)
#     user_id = fields.Many2one('res.users', string='Responsible', readonly=True)

#     site_id = fields.Many2one('re.site', string='Site', readonly=True)
#     block_id = fields.Many2one('re.block', string='Block', readonly=True)
#     floor_id = fields.Many2one('re.floor', string='Floor', readonly=True)

#     loan_line_count = fields.Integer(string="Installments Count", readonly=True)
#     installment_paid_count = fields.Integer(string="Paid Installments", readonly=True)
#     installment_unpaid_count = fields.Integer(string="Unpaid Installments", readonly=True)
#     installment_total_amount = fields.Float(string="Installment Total", readonly=True)
#     installment_paid_amount = fields.Float(string="Installment Paid", readonly=True)
#     installment_balance_amount = fields.Float(string="Installment Balance", readonly=True)

#     installment_number = fields.Char(string='Installment Number', readonly=True)
#     installment_name = fields.Char(string='Installment Name', readonly=True)

#     discount_total = fields.Float(string='Total Discount', readonly=True)

#     def init(self):
#         tools.drop_view_if_exists(self._cr, 'report_ownership_contract_bi')
#         self._cr.execute("""
#             create or replace view report_ownership_contract_bi as (
#                 select min(lro.id) as id,
#                     oc.name,
#                     oc.date as contract_date,
#                     oc.partner_id as partner_id,
#                     oc.site_id as site_id,
#                     oc.block_id as block_id,
#                     oc.building_id as contract_building_id,
#                     oc.floor_id as floor_id,
#                     oc.building_unit_id as product_template_id,
#                     oc.state as state,
#                     lro.date as due_date,
#                     oc.user_id as user_id,
#                     (lro.amount - am.amount_residual) as paid,
#                     am.amount_residual as unpaid,
#                     lro.invoice_id as invoice_id,
#                     am.payment_state as payment_state,
#                     am.state as invoice_state,
#                     lro.amount as amount,
#                     lro.number as installment_number,
#                     lro.name as installment_name,
#                     COUNT(lro.id) as loan_line_count,
#                     COUNT(CASE WHEN lro.amount - am.amount_residual <= 0 THEN 1 ELSE NULL END) as installment_paid_count,
#                     COUNT(CASE WHEN lro.amount - am.amount_residual > 0 THEN 1 ELSE NULL END) as installment_unpaid_count,
#                     SUM(lro.amount) as installment_total_amount,
#                     SUM(lro.amount - am.amount_residual) as installment_paid_amount,
#                     SUM(am.amount_residual) as installment_balance_amount,
#                     SUM(COALESCE(lro.original_amount, 0) - lro.amount) as discount_total  -- NEW
#                 FROM ownership_contract oc
#                 LEFT JOIN loan_line_rs_own lro ON oc.id = lro.loan_id
#                 LEFT JOIN account_move am ON am.id = lro.invoice_id
#                 LEFT JOIN loan_line_rs_own l ON l.loan_id = oc.id
#                 GROUP BY
#                     oc.name, 
#                     oc.date, 
#                     oc.partner_id,
#                     oc.site_id,
#                     oc.block_id,
#                     oc.building_id,
#                     oc.floor_id,
#                     oc.building_unit_id,
#                     oc.state, 
#                     lro.date, 
#                     oc.user_id, 
#                     lro.amount, 
#                     am.amount_residual, 
#                     am.state, 
#                     am.payment_state, 
#                     lro.invoice_id, 
#                     lro.number,
#                     lro.name
#             )""")
            