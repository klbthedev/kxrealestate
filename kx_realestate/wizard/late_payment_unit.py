import time
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models
from odoo.tools.translate import _

class late_payment_unit_check(models.TransientModel):
    _name = 'late.payment.unit.check'

    building_unit= fields.Many2many('product.template', domain=[('is_property', '=', True)], string='Filter on units',
                                    help="Only selected units will be printed. Leave empty to print all units.")
    date_start= fields.Date(string='From', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_end= fields.Date(string='To', required=True, default= lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def check_report(self):
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'ownership.contract',
            'form': data
        }
        return self.env.ref('kx_realestate.late_payments_units').report_action([],data=datas)
