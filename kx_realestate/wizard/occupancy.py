from odoo import fields, models
from odoo.tools.translate import _

class occupancy_check(models.TransientModel):
    _name = 'occupancy.check'

    building_check = fields.Boolean(string='Filter by building')
    building_ids = fields.Many2many('building.building', string='Building',
                                    help="Only selected building will be printed.  Leave empty to print all building.")
    region_check = fields.Boolean(string='Filter by region')
    # region_ids = fields.Many2many('regions.regions', string='Region',
    #                             help="Only selected Regions will be printed. Leave empty to print all Regions.")
    unit_check = fields.Boolean('Filter by building unit')
    unit_ids = fields.Many2many('product.template', domain=[('is_property', '=', True)], string='Building Unit',
                                help="Only selected building unit will be printed. Leave empty to print all building unit.")

    def check_report(self):
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'product.template',
            'form': data
        }
        return self.env.ref('kx_realestate.report_unit_occupancy').report_action([],data=datas)
