import time
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models
from odoo.tools.translate import _

class due_payment_unit_check(models.TransientModel):
    _name = 'due.payment.unit.check'

    building_unit_id = fields.Many2many('product.template', string='Filter on unit',domain=[('is_property', '=', True)],
                                        help="Only selected unit will be printed. Leave empty to print all unit.")
    date_start = fields.Date('From',required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_end = fields.Date('To',required=True, default=lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def check_report(self):
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'ownership.contract',
            'form': data
        }
        return self.env.ref('kx_realestate.due_payments_units').report_action([],data=datas)
