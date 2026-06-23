from odoo import fields, models, tools


class report_units(models.Model):
    _name = "units.report"
    _description = "Units Report"
    _auto = False

    site_id = fields.Many2one('re.site', string='Site', readonly=True)
    block_id = fields.Many2one('re.block', string='Block', readonly=True)
    building_id = fields.Many2one('building.building', string='Building')
    floor_id = fields.Many2one('re.floor', string='Floor', readonly=True)
    building_description_id = fields.Many2one('building.description', string='Building Description')
    partner_id = fields.Many2one('res.partner', string='Owner')
    rooms = fields.Char(string='Rooms', size=32)
    building_status_id = fields.Many2one('building.status', string='Building Unit Status')
    building_type_id = fields.Many2one('building.type', string='Building Unit Type')
    stock_state = fields.Selection([
        ('raw_material', 'Raw Material'),
        ('wip', 'Work in Progress'),
        ('semi_finished', 'Semi-finished'),
        ('finished', 'Finished'),
        ('sold', 'Sold'),
        ('leased', 'Leased'),
        ('blocked', 'Blocked'),
    ], string='Construction Stock State', readonly=True)
    units = fields.Integer(string='Units', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'units_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW units_report AS (
                SELECT
                    MIN(pt.id) AS id,
                    pt.site_id AS site_id,
                    pt.block_id AS block_id,
                    pt.building_id AS building_id,
                    pt.floor_id AS floor_id,
                    pt.building_description_id AS building_description_id,
                    pt.partner_id AS partner_id,
                    pt.rooms::varchar AS rooms,
                    pt.building_status_id AS building_status_id,
                    pt.building_type_id AS building_type_id,
                    pt.stock_state AS stock_state,
                    COUNT(pt.id) AS units
                FROM product_template pt
                WHERE pt.is_property = TRUE
                GROUP BY
                    pt.site_id,
                    pt.block_id,
                    pt.building_id,
                    pt.floor_id,
                    pt.building_description_id,
                    pt.partner_id,
                    pt.rooms,
                    pt.building_status_id,
                    pt.building_type_id,
                    pt.stock_state
            )
        """)
