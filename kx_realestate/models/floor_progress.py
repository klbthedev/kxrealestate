from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RealEstateFloorProgress(models.Model):
    _name = "re.floor.progress"
    _description = "Floor Progress Update"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'progress_date desc, id desc'

    approved_by_id = fields.Many2one('res.users', string='Approved By')
    building_id = fields.Many2one('building.building', related='floor_id.building_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    floor_id = fields.Many2one('re.floor', string='Floor', required=True, ondelete='cascade', tracking=True)
    note = fields.Html(string='Notes')
    percent_complete = fields.Float(string='Completion %', required=True, tracking=True)
    progress_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    stage = fields.Selection(
        selection='_selection_progress_stage',
        default='planned',
        required=True,
        tracking=True,
    )
    user_id = fields.Many2one('res.users', string='Updated By', default=lambda self: self.env.user, required=True)

    @api.model
    def _selection_progress_stage(self):
        floor_id = self.env.context.get('default_floor_id')
        building_type_id = False
        if floor_id:
            floor = self.env['re.floor'].browse(floor_id)
            building_type_id = floor.building_type_id.id
        return self.env['re.floor.stage'].get_stage_selection(building_type_id=building_type_id)

    @api.constrains('percent_complete')
    def _check_percent_complete(self):
        for progress in self:
            if progress.percent_complete < 0 or progress.percent_complete > 100:
                raise ValidationError('Completion percentage must be between 0 and 100.')
            allowed_codes = [
                code for code, _name in self.env['re.floor.stage'].get_stage_selection(
                    building_type_id=progress.floor_id.building_type_id.id
                )
            ]
            if progress.stage and progress.stage not in allowed_codes:
                raise ValidationError('Selected stage is not valid for this floor building type.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.floor_id.write({
                'progress_stage': rec.stage,
            })
        return records

    def write(self, vals):
        res = super().write(vals)
        if {'stage', 'percent_complete'} & set(vals.keys()):
            for rec in self:
                rec.floor_id.write({
                    'progress_stage': rec.stage,
                })
        return res
