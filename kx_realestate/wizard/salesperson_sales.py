import time
from datetime import datetime
from odoo import fields, models
from odoo.tools.translate import _
from dateutil import relativedelta

class SalespersonSalesCheck(models.TransientModel):
    _name = 'salesperson.sales.check'

    date_from = fields.Date(string='From', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date(string='To', required=True, default= lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],)
    user_ids = fields.Many2many('res.users', string='Salesperson',
                                help="Only selected salespersons will be printed. Leave empty to print all salesperson.")

    def check_report(self):
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'ownership.contract',
            'form': data
        }
        return self.env.ref('kx_realestate.report_sales_rep_rs').report_action([],data=datas)
