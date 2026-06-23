from odoo import api, fields, models
from odoo.tools.translate import _

class LatlngLine(models.Model):
    _name = "latlng.line"
    _rec_name = 'unit_id'

    latitude = fields.Float(string='Latitude', digits=(9, 6), required=True)
    longitude = fields.Float(string='Longitude', digits=(9, 6), required=True)
    # region_id = fields.Many2one('regions.regions', string='Region')
    state = fields.Selection(string='State', related='unit_id.state', store=True, readonly=True)
    unit_id = fields.Many2one('product.template', string='Unit', domain=[('is_property', '=', True)])
    url = fields.Char(string='URL', digits=(9, 6), required=True)

    @api.onchange('unit_id')
    def onchange_unit(self):
        link = '#id=33&cids=1&action=317&model=product.template&view_type=form&menu_id=205'
        self.url = link

    @api.onchange('url')
    def onchange_url(self):
        if self.url:
            url = self.url
            self.unit_id = int(((url.split("#")[1]).split("&")[0]).split("=")[1])
        else:
            self.unit_id = None
            self.state = None
