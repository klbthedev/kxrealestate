from odoo import api, fields, models, tools

class rental_contract_bi_report(models.Model):
    _name = "report.rental.contract.bi"
    _description = "Rental Contracts Statistics"
    _auto = False
    _order = 'contract_date asc'

    amount = fields.Float(string='Amount', digits=(16, 4), readonly=True)
    contract_building_id = fields.Many2one('building.building', string='Building', readonly=True)
    contract_date = fields.Date(string='Contract Date', readonly=True)
    # contract_region_id = fields.Many2one('regions.regions', string='Region', readonly=True)
    product_template_id = fields.Many2one('product.template', string='Property', readonly=True)
    due_date = fields.Date(string='Due Date', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')], readonly=True)
    name = fields.Char(string='Contract', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    paid = fields.Float(string='Paid Amount', readonly=True)
    payment_state = fields.Selection([
                                    ('not_paid', 'Not Paid'),
                                    ('in_payment', 'In Payment'),
                                    ('paid', 'Paid'),
                                    ('partial', 'Partially Paid'),
                                    ('reversed', 'Reversed'),
                                    ('invoicing_legacy', 'Invoicing App Legacy'),
                                    ], string='Payment State', readonly=True)
    state = fields.Selection([('draft','Draft'), ('confirmed','Confirmed'), ('cancel','Canceled')], string='State')
    user_id = fields.Many2one('res.users', string='Responsible', readonly=True)
    unpaid = fields.Float(string='Balance', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_rental_contract_bi')
        self._cr.execute("""
            create or replace view report_rental_contract_bi as (
                select min(lro.id) as id,
                oc.name,
                oc.date as contract_date,
                oc.partner_id as partner_id,
                oc.building_unit_id as product_template_id,
                oc.building as contract_building_id,
                lro.date as due_date,
                oc.state as state,
		        oc.user_id as user_id,
                (lro.amount-am.amount_residual) as paid,
                am.amount_residual as unpaid,
                lro.invoice_id as invoice_id,
                am.payment_state as payment_state,
                am.state as invoice_state,
                lro.amount as amount
                FROM rental_contract oc
                LEFT JOIN loan_line_rs_rent lro ON oc.id = lro.loan_id
                LEFT JOIN account_move am ON am.id= lro.invoice_id
                GROUP BY
                    oc.state,
                    lro.paid,
                    lro.amount,
                    am.amount_residual,
                    am.state,
                    am.payment_state ,
                    lro.invoice_id,
                    oc.name,
                    oc.partner_id,
                    oc.building_unit_id,
                    oc.building,
                    oc.date,
                    lro.date,
                    oc.user_id
           )""")
