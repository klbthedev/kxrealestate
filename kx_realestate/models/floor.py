from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class RealEstateFloorStatus(models.Model):
    _name = "re.floor.status"
    _description = "Real Estate Floor Status"

    floor_id = fields.Many2one(
        're.floor',
        string='Floor',
        ondelete='cascade'
    )
    building_id = fields.Many2one(
        'building.building',
        related='floor_id.building_id',
        store=True,
        readonly=True
    )
    block_id = fields.Many2one(
        're.block',
        related='floor_id.block_id',
        store=True,
        readonly=True
    )
    building_type_id = fields.Many2one(
        'building.type',
        related='floor_id.building_type_id',
        store=True,
        readonly=True
    )
    floor_status_id_date = fields.Datetime(default=fields.Datetime.now)
    floor_status_id = fields.Many2one(
        're.floor.stage',
        string="Floor Stage",
        domain="[('active', '=', True), '|', ('building_type_id', '=', False), ('building_type_id', '=', building_type_id)]",
        tracking=True,
        group_expand='_read_group_stage_ids',
        required=1,
    )

    ##############################################################################################
    # update installment records
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            loan_lines = self.env['loan.line.rs.own'].search([
                ('selected_floor_id', '=', rec.floor_id.id),
                ('progress_floor_stage_id', '=', rec.floor_status_id.id),
            ])
            if loan_lines.trigger_type == 'construction':
                loan_lines.write({
                    'status_complete_date': rec.floor_status_id_date,
                })
                loan_lines.write({
                    'date': rec.floor_status_id_date + timedelta(days=loan_lines.payment_term_date or 0)
                })
        return records
    ##############################################################################################
    # update installment records
    def write(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            loan_lines = self.env['loan.line.rs.own'].search([
                ('selected_floor_id', '=', rec.floor_id.id),
                ('progress_floor_stage_id', '=', rec.floor_status_id.id),
            ])
            if loan_lines.trigger_type == 'construction':
                loan_lines.write({
                    'status_complete_date': rec.floor_status_id_date,
                })
                loan_lines.write({
                    'date': rec.floor_status_id_date + timedelta(days=loan_lines.payment_term_date or 0)
                })
        return records    
    ##############################################################################################

class RealEstateFloor(models.Model):
    _name = "re.floor"
    _description = "Real Estate Floor"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'building_id, sequence, level_number, id'


    # name = fields.Char(required=True)
    matterport_model_id = fields.Char("Matterport Model ID")
    matterport_embed_url = fields.Char(compute="_compute_embed_url",)
    matterport_iframe = fields.Html(compute="_compute_iframe", sanitize=False)    

    def _compute_embed_url(self):
        for rec in self:
            if rec.matterport_model_id:
                rec.matterport_embed_url = (f"https://my.matterport.com/show/?m={rec.matterport_model_id}")
            else:
                rec.matterport_embed_url = False

    def action_open_matterport(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'matterport_viewer',
            'params': {
                'url': self.matterport_embed_url,
                'name': self.name,
            }
        }

    def _compute_iframe(self):
        for rec in self:
            if rec.matterport_model_id:
                url = f"https://my.matterport.com/show/?m={rec.matterport_model_id}"
                rec.matterport_iframe = f"""
                    <iframe src="{url}"
                        width="100%"
                        height="500px"
                        frameborder="0"
                        allowfullscreen
                        allow="xr-spatial-tracking">
                    </iframe>
                """
            else:
                rec.matterport_iframe = "<p>No 3D tour available.</p>"

    active = fields.Boolean(default=True)
    block_id = fields.Many2one('re.block', related='building_id.block_id', store=True, readonly=True)
    building_id = fields.Many2one('building.building', string='Building', required=True, ondelete='cascade', tracking=True)
    # building_type_id = fields.Many2one('building.type', related='building_id.building_type_id', store=True, readonly=True)
    building_type_id = fields.Many2one(
        'building.type',
        related='building_id.building_type_id',
        store=True,
        readonly=True
    )
    code = fields.Char(string='Code', tracking=True, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    latest_progress_id = fields.Many2one('re.floor.progress', compute='_compute_progress_snapshot', string='Latest Progress')
    level_number = fields.Integer(string='Floor Number', required=True, tracking=True)
    name = fields.Char(required=True, tracking=True)
    note = fields.Html(string='Notes')

    progress_percent = fields.Float(
        string='Progress %',
        compute='_compute_progress_percent',
        store=True,
        readonly=True,
        tracking=True,
    )
    stage_id = fields.Many2one(
        're.floor.stage',
        string="Floor Stage",
        domain="[('active', '=', True), '|', ('building_type_id', '=', False), ('building_type_id', '=', building_type_id)]",
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    floor_stage_ids = fields.One2many('re.floor.status','floor_id', string='Floor status')
    # stage_id_date = fields.Datetime(default=fields.Datetime.now)
    progress_line_ids = fields.One2many('re.floor.progress', 'floor_id', string='Progress History')
    sequence = fields.Integer(default=10)
    site_id = fields.Many2one('re.site', related='building_id.site_id', store=True, readonly=True)
    unit_ids = fields.One2many('product.template', 'floor_id', string='Units')
    unit_count = fields.Integer(compute='_compute_unit_count', string='Units')
    
    selected_floor = fields.One2many('loan.line.rs.own', 'selected_floor_id', string='Floor #')
    
    _sql_constraints = [
        ('floor_code_building_uniq', 'unique(code, building_id)', 'Floor code must be unique per building.'),
        ('floor_level_building_uniq', 'unique(level_number, building_id)', 'Floor number must be unique per building.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == '/':
                building = self.env['building.building'].browse(vals.get('building_id'))
                prefix = building.code + '/' if building and building.code else ''
                vals['code'] = prefix + (self.env['ir.sequence'].next_by_code('re.floor') or '/')
            if not vals.get('stage_id') and vals.get('building_id'):
                building = self.env['building.building'].browse(vals['building_id'])
                stage = self.env['re.floor.stage'].search([
                    ('active', '=', True),
                    '|',
                    ('building_type_id', '=', False),
                    ('building_type_id', '=', building.building_type_id.id)
                ], order='sequence asc', limit=1)

                if stage:
                    vals['stage_id'] = stage.id

        return super().create(vals_list)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        building_type_id = self.env.context.get('default_building_type_id')
        stage_domain = [('active', '=', True)]
        if building_type_id:
            stage_domain.extend([
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', building_type_id),
            ])
        return self.env['re.floor.stage'].search(stage_domain, order='sequence, id')

    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.building_id:
            stages = self.env['re.floor.stage'].search([
                ('active', '=', True),
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', self.building_id.building_type_id.id)
            ], order='sequence asc', limit=1)

            if stages:
                self.stage_id = stages.id

    @api.depends('unit_ids')
    def _compute_unit_count(self):
        for floor in self:
            floor.unit_count = len(floor.unit_ids)

    @api.depends('progress_line_ids.progress_date')
    def _compute_progress_snapshot(self):
        for floor in self:
            progress = floor.progress_line_ids.sorted(
                key=lambda line: (line.progress_date or fields.Date.today(), line.id),
                reverse=True,
            )[:1]
            progress = progress[:1]
            floor.latest_progress_id = progress.id if progress else False


    @api.depends('stage_id', 'building_type_id')
    def _compute_progress_percent(self):
        for floor in self:
            stages = self.env['re.floor.stage'].search([
                ('active', '=', True),
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', floor.building_type_id.id)
            ], order='sequence asc')

            if not stages:
                floor.progress_percent = 0
                continue

            try:
                index = list(stages.ids).index(floor.stage_id.id) + 1
            except ValueError:
                index = 0

            floor.progress_percent = (index / len(stages)) * 100 if index else 0
    # @api.constrains('progress_stage', 'building_type_id')
    def _check_progress_stage_for_building_type(self):
        for floor in self:
            allowed_codes = [
                code for code, _name in self.env['re.floor.stage'].get_stage_selection(
                    building_type_id=floor.building_type_id.id
                )
            ]
            if floor.progress_stage and floor.progress_stage not in allowed_codes:
                raise ValidationError(_('Selected progress stage is not configured for this building type.'))

    def action_view_units(self):
        self.ensure_one()
        return {
            'name': _('Units'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.unit_ids.ids)],
            'context': {
                'default_is_property': True,
                'form_view_ref': 'kx_realestate.building_unit_form',
                'tree_view_ref': 'kx_realestate.building_unit_list',
            },
            'views': [
                (self.env.ref('kx_realestate.building_unit_list').id, 'list'),
                (self.env.ref('kx_realestate.building_unit_form').id, 'form'),
            ],
        }

    def action_view_building(self):
        self.ensure_one()
        return {
            'name': _('Building'),
            'type': 'ir.actions.act_window',
            'res_model': 'building.building',
            'view_mode': 'form',
            'res_id': self.building_id.id,
            'target': 'current',
        }


    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            self.env['loan.line.rs.own'].process_selected_floor_stage_notifications(self)
        return res