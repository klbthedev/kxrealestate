from odoo import api, fields, models


class RealEstateUnitStage(models.Model):
    _name = "re.unit.stage"
    _description = "Unit Progress Stage"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    building_type_id = fields.Many2one('building.type', string='Building Type')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text()

    _sql_constraints = [
        (
            'unit_stage_code_type_uniq',
            'unique(code, building_type_id)',
            'Unit stage code must be unique per building type.',
        ),
    ]

    @api.model
    def _default_stage_pairs(self):
        return [
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
        ]

    @api.model
    def get_stage_selection(self, building_type_id=False):
        domain = [('active', '=', True)]
        if building_type_id:
            domain.extend(['|', ('building_type_id', '=', False), ('building_type_id', '=', building_type_id)])
        stages = self.search(domain, order='sequence, id')
        if stages:
            return [(stage.code, stage.name) for stage in stages]
        return self._default_stage_pairs()

    @api.model
    def get_stage_rank_map(self, building_type_id=False):
        selection = self.get_stage_selection(building_type_id=building_type_id)
        return {code: idx for idx, (code, _label) in enumerate(selection)}
