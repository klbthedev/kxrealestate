# from odoo import models, fields, api

# class MaintenanceDashboard(models.TransientModel):
#     _name = 'my.dashboard'
#     _description = 'Palm Dashboard'
#     #########################################################################
#     name = fields.Char(string='Dashboard', default='Dashboard')
#     # Filters 
#     date_from = fields.Date(string="From Date")
#     date_to = fields.Date(string="To Date")
#     # KPIs
#     requested_payment_count = fields.Integer(string='Requested Payment Count')
#     trigger_type_construction_count = fields.Integer(string='Trigger Type Construction Count')
#     trigger_type_date_count = fields.Integer(string='Trigger Type Date Count')    
#     #########################################################################
#     def _get_dashboard_data(self, date_from=None, date_to=None):
#         query = """
#             SELECT
#                 COUNT(CASE WHEN payment_request_letter = 'yes' THEN 1 END),
#                 COUNT(CASE WHEN trigger_type = 'construction' THEN 1 END),
#                 COUNT(CASE WHEN trigger_type = 'date' THEN 1 END)
#             FROM loan_line_rs_own
#             WHERE 1=1
#         """
#         params = []
#         if date_from:
#             query += " AND date >= %s"
#             params.append(date_from)
#         if date_to:
#             query += " AND date <= %s"
#             params.append(date_to)
#         self.env.cr.execute(query, params)
#         result = self.env.cr.fetchone()
#         return {
#             'requested_payment_count': result[0] or 0,
#             'trigger_type_construction_count': result[1] or 0,
#             'trigger_type_date_count': result[2] or 0,
#         }
#     #########################################################################
#     @api.model
#     def default_get(self, fields_list):
#         vals = super().default_get(fields_list)
#         vals.update(self._get_dashboard_data())
#         return vals
#     #########################################################################
#     def action_refresh_dashboard(self):
#         self.ensure_one()
#         values = self._get_dashboard_data(
#             self.date_from,
#             self.date_to
#         )
#         self.write(values)
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'reload',
#         }
#     #########################################################################
    

from odoo import models, fields, api


class MaintenanceDashboard(models.TransientModel):
    _name = 'my.dashboard'
    _description = 'Palm KPI Dashboard'

    name = fields.Char(default="Dashboard")

    # Filters
    date_from = fields.Date(string="From Date", default='2026-1-1')
    date_to = fields.Date(string="To Date", default='2026-12-31')

    # KPIs
    requested_payment_count = fields.Integer(string='Requested Payment Count')
    trigger_type_construction_count = fields.Integer(string='Construction Trigger Count')
    trigger_type_date_count = fields.Integer(string='Date Trigger Count')

    # -------------------------
    # Core KPI computation
    # -------------------------
    def _compute_kpis(self):
        query = """
            SELECT
                COUNT(*) FILTER (WHERE payment_request_letter = 'yes') AS requested_payment_count,
                COUNT(*) FILTER (WHERE trigger_type = 'construction') AS construction_count,
                COUNT(*) FILTER (WHERE trigger_type = 'date') AS date_count
            FROM loan_line_rs_own
            WHERE 1=1
        """
        # SELECT
        #         COUNT(CASE WHEN payment_request_letter = 'yes' THEN 1 END),
        #         COUNT(CASE WHEN trigger_type = 'construction' THEN 1 END),
        #         COUNT(CASE WHEN trigger_type = 'date' THEN 1 END)
        #     FROM loan_line_rs_own
        #     WHERE 1=1

        params = []

        if self.date_from:
            query += " AND date >= %s"
            params.append(self.date_from)

        if self.date_to:
            query += " AND date <= %s"
            params.append(self.date_to)

        self.env.cr.execute(query, params)
        result = self.env.cr.fetchone() or (0, 0, 0)

        self.requested_payment_count = result[0] or 0
        self.trigger_type_construction_count = result[1] or 0
        self.trigger_type_date_count = result[2] or 0

    # -------------------------
    # Auto refresh on change
    # -------------------------
    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        for rec in self:
            rec._compute_kpis() 