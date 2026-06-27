import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class RealEstateBuildingStatus(models.Model):
    _name = "re.building.status"
    _description = "Real Estate Building Status"

    building_id = fields.Many2one(
        'building.building',
        string='Building',
        ondelete='cascade'
    )
    block_id = fields.Many2one(
        're.block',
        related='building_id.block_id',
        store=True,
        readonly=True
    )
    building_type_id = fields.Many2one(
        'building.type',
        related='building_id.building_type_id',
        store=True,
        readonly=True
    )
    building_status_id_date = fields.Datetime(default=fields.Datetime.now)
    building_status_id = fields.Many2one(
        're.building.stage',
        string="Building Stage",
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
            for line in loan_lines:
                if line.trigger_type == 'construction':
                    line.write({
                        'status_complete_date': rec.floor_status_id_date,
                        'date': rec.floor_status_id_date + timedelta(days=line.payment_term_date or 0)
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



class Building(models.Model):
    _name = "building.building"
    _description = "Building"
    _inherit = ['mail.thread']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == 'New':
                block = self.env['re.block'].browse(vals.get('block_id'))
                prefix = block.code + '/' if block and block.code else ''
                vals['code'] = prefix + (self.env['ir.sequence'].next_by_code('building.building') or 'New')
            if not vals.get('stage_id') and vals.get('building_type_id'):
                stage = self.env['re.building.stage'].search([
                    ('active', '=', True),
                    '|',
                    ('building_type_id', '=', False),
                    ('building_type_id', '=', vals['building_type_id'])
                ], order='sequence asc', limit=1)
                if stage:
                    vals['stage_id'] = stage.id
        return super().create(vals_list)

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            from odoo.addons.kx_realestate.hooks import migrate_legacy_stage_data
            migrate_legacy_stage_data(self.env)
        except Exception:
            _logger.exception('kx_realestate: legacy stage migration failed')

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


    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one(
        'res.country.state',
        string='State / Region',
        domain="[('country_id', '=?', country_id)]",
    )
    city = fields.Char(string='City')
    zone = fields.Char(string='Zone')
    sub_city = fields.Char(string='Sub-city')
    kebele = fields.Char(string='Kebele')
    woreda = fields.Char(string='Woreda')
    gps_latitude = fields.Float(string='GPS Latitude', digits=(9, 6))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(9, 6))
    land_title_ref = fields.Char(string='Land title reference')
    parcel_id = fields.Char(string='Parcel / plot ID')
    title_deed_no = fields.Char(string='Title Deed / Ownership Certificate No.')
    title_deed_date = fields.Date(string='Title Deed Date')
    utility_electric_ref = fields.Char(string='Electricity utility account ref.')
    utility_water_ref = fields.Char(string='Water utility account ref.')
    utility_other_ref = fields.Char(string='Other utility ref.')
    stage_id = fields.Many2one(
        're.building.stage',
        string="Building Stage",
        domain="[('active', '=', True), '|', ('building_type_id', '=', False), ('building_type_id', '=', building_type_id)]",
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    progress_percent = fields.Float(
        string='Progress %',
        compute='_compute_progress_percent',
        store=True,
        readonly=True,
        tracking=True,
    )

    _sql_constraints = [
        (
            'building_title_deed_no_uniq',
            'unique(title_deed_no)',
            'Title Deed / Ownership Certificate No. must be unique.',
        ),
    ]

    building_stage_ids = fields.One2many('re.building.status','building_id', string='Building status')
    unit_count = fields.Integer(string='Units', compute='_compute_building_smart_counts')
    floor_count = fields.Integer(string='Floors', compute='_compute_building_smart_counts')
    reservation_count = fields.Integer(string='Reservations', compute='_compute_building_smart_counts')
    ownership_contract_count = fields.Integer(string='Sales contracts', compute='_compute_building_smart_counts')
    # rental_contract_count = fields.Integer(string='Rental contracts', compute='_compute_building_smart_counts')

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    active = fields.Boolean(string='Active',
            help="If the active field is set to False, it will allow you to hide the top without removing it.", default=True)
    amenity_ids = fields.Many2many('re.amenity', 'building_amenity_rel', 'building_id', 'amenity_id', string='Amenities')
    air_condition = fields.Selection([('unknown','Unknown'),
                                    ('central','Central'),
                                    ('partial','Partial'),
                                    ('none', 'None')], string='Air Condition')
    address = fields.Char(string='Address')
    account_id = fields.Many2one('account.account', string='Income Account')
    building_attachment_line_ids = fields.One2many("building.attachment.line", "building_id", string="Documents")
    balcony = fields.Float(string='Balconies m²')
    block_id = fields.Many2one('re.block', string='Block', tracking=True)
    building_unit_area = fields.Float(string='Property Area m²')
    building_image_ids = fields.One2many('building.images', 'building_id', string="Building Images", copy=True)
    building_status_id = fields.Many2one('building.status',string='Property Status')
    building_type_id = fields.Many2one('building.type', string='Property Type')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    construction_date = fields.Date(string='Construction Date')
    category = fields.Char(string='Category', size=16)
    code = fields.Char(string='Code', readonly=True)
    date_added = fields.Date(string='Date Added to Notarization')
    description = fields.Text(string='Description')
    east = fields.Char(string='Eastern border  by')
    electricity_meter = fields.Char(string='Electricity meter', size=16)
    floor = fields.Char(string='Floor', size=16)
    freight_lift = fields.Integer(string='Freight Elevators')
    garage_included = fields.Integer(string='Garage included')
    garden = fields.Float(string='Garden m²')
    gross_area = fields.Float(string='Land Area m²')
    handicap_accessible = fields.Boolean(string='Handicap Accessible')
    heating = fields.Selection([('unknown','unknown'),
                                ('none','none'),
                                ('tiled_stove', 'tiled stove'),
                                ('stove', 'stove'),
                                ('central','central heating'),
                                ('self_contained_central','self-contained central heating')], string='Heating')
    heating_source = fields.Selection([('unknown','unknown'),
                                    ('electricity','Electricity'),
                                    ('wood','Wood'),
                                    ('pellets','Pellets'),
                                    ('oil','Oil'),
                                    ('gas','Gas'),
                                    ('district','District Heating')], string='Heating Source')
    internet = fields.Boolean(string='Internet')
    launch_date = fields.Date(string='Launching Date')
    license_code = fields.Char(string='License Code', size=16)
    license_date = fields.Date(string='License Date')
    license_location = fields.Char(string='License Notarization')
    name = fields.Char(string='Name', required=True)
    no_of_floors = fields.Integer(string='Floors')
    north = fields.Char(string='Northen border by')
    note = fields.Html(string='Notes')
    note_sales = fields.Text(string='Note Sales Folder')
    old_property = fields.Boolean(string='Old Property')
    parking_place_rentable = fields.Boolean(string='Parking rentable')
    partner_id = fields.Many2one('res.partner',string='Owner')
    floor_ids = fields.One2many('re.floor', 'building_id', string='Floors')
    property_floor_plan_image_ids = fields.One2many('floor.plans', 'building_id', string="Floor Plans", copy=True)
    props_per_floors = fields.Integer(string='Unit per Floor')
    purchase_date = fields.Date(string='Purchase Date')
    passenger_lift = fields.Integer(string='Passenger Elevators')
    # region_id = fields.Many2one('regions.regions', string='Region')
    rooms = fields.Char(string='Rooms', size=32)
    solar_electric = fields.Boolean(string='Solar Electric System')
    solar_heating = fields.Boolean(string='Solar Heating System')
    selling_price = fields.Integer(string='Price')
    staircase = fields.Char(string='Staircase', size=8)
    surface = fields.Integer(string='Surface')
    sort = fields.Integer(string='Sort')
    sequence = fields.Integer(string='Sequence')
    south = fields.Char(string='Southern border by')
    site_id = fields.Many2one('re.site', string='Site', tracking=True)
    terraces = fields.Integer(string='Terraces m²')
    telephon = fields.Boolean(string='Telephone')
    tv_cable = fields.Boolean(string='Cable TV')
    tv_sat = fields.Boolean(string='SAT TV')
    target_lease = fields.Integer(string='Target Lease')
    unit_ids = fields.Many2many('product.template', string='Properties')
    usage = fields.Selection([('unlimited','unlimited'),
                            ('office','Office'),
                            ('shop','Shop'),
                            ('flat','Flat'),
                            ('rural','Rural Property'),
                            ('parking','Parking')], string='Usage')
    water_meter = fields.Char(string='Water meter', size=16)
    west = fields.Char(string='Western border by')

    @api.onchange('state_id')
    def _onchange_state_id_set_country(self):
        for building in self:
            if building.state_id and building.state_id.country_id:
                building.country_id = building.state_id.country_id

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
        return self.env['re.building.stage'].search(stage_domain, order='sequence, id')

    @api.onchange('building_type_id')
    def _onchange_building_type_id_stage(self):
        if self.building_type_id:
            stages = self.env['re.building.stage'].search([
                ('active', '=', True),
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', self.building_type_id.id)
            ], order='sequence asc', limit=1)
            if stages:
                self.stage_id = stages.id

    @api.depends('stage_id', 'building_type_id')
    def _compute_progress_percent(self):
        for rec in self:
            stages = self.env['re.building.stage'].search([
                ('active', '=', True),
                '|',
                ('building_type_id', '=', False),
                ('building_type_id', '=', rec.building_type_id.id)
            ], order='sequence asc')

            if not stages:
                rec.progress_percent = 0
                continue

            try:
                index = list(stages.ids).index(rec.stage_id.id) + 1
            except ValueError:
                index = 0

            rec.progress_percent = (index / len(stages)) * 100 if index else 0

    @api.depends('floor_ids', 'unit_ids')
    def _compute_building_smart_counts(self):
        for b in self:
            b.floor_count = len(b.floor_ids)
        if not self.ids:
            for b in self:
                b.unit_count = 0
                b.reservation_count = 0
                b.ownership_contract_count = 0
                # b.rental_contract_count = 0
            return
        Unit = self.env['product.template']
        Res = self.env['unit.reservation']
        Own = self.env['ownership.contract']
        # Rent = self.env['rental.contract']
        unit_map = {
            g['building_id'][0]: g['__count']
            for g in Unit.read_group(
                [('building_id', 'in', self.ids), ('is_property', '=', True)],
                ['__count'],
                ['building_id'],
                lazy=False,
            )
            if g.get('building_id')
        }
        res_map = {
            g['building_id'][0]: g['__count']
            for g in Res.read_group(
                [('building_id', 'in', self.ids)],
                ['__count'],
                ['building_id'],
                lazy=False,
            )
            if g.get('building_id')
        }
        own_map = {
            g['building_id'][0]: g['__count']
            for g in Own.read_group(
                [('building_id', 'in', self.ids)],
                ['__count'],
                ['building_id'],
                lazy=False,
            )
            if g.get('building_id')
        }
        # rent_map = {
        #     g['building_id'][0]: g['__count']
        #     for g in Rent.read_group(
        #         [('building_id', 'in', self.ids)],
        #         ['__count'],
        #         ['building_id'],
        #         lazy=False,
        #     )
        #     if g.get('building_id')
        # }
        for b in self:
            b.unit_count = unit_map.get(b.id, 0)
            b.reservation_count = res_map.get(b.id, 0)
            b.ownership_contract_count = own_map.get(b.id, 0)
            # b.rental_contract_count = rent_map.get(b.id, 0)

    def _action_window(self, name, res_model, domain, context=None):
        self.ensure_one()
        action = {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }
        if context:
            action['context'] = context
        return action

    def action_view_property_units(self):
        self.ensure_one()
        return self._action_window(
            _('Units'),
            'product.template',
            [('building_id', '=', self.id), ('is_property', '=', True)],
            {
                'default_building_id': self.id,
                'default_is_property': True,
                'form_view_ref': 'kx_realestate.building_unit_form',
                'tree_view_ref': 'kx_realestate.building_unit_list',
            },
        )

    def action_view_floors(self):
        self.ensure_one()
        return self._action_window(
            _('Floors'),
            're.floor',
            [('building_id', '=', self.id)],
            {'default_building_id': self.id},
        )

    def action_view_reservations(self):
        self.ensure_one()
        return self._action_window(
            _('Reservations'),
            'unit.reservation',
            [('building_id', '=', self.id)],
            {'default_building_id': self.id},
        )

    def action_view_ownership_contracts(self):
        self.ensure_one()
        return self._action_window(
            _('Ownership contracts'),
            'ownership.contract',
            [('building_id', '=', self.id)],
            {'default_building_id': self.id},
        )

    # def action_view_rental_contracts(self):
    #     self.ensure_one()
    #     return self._action_window(
    #         _('Rental contracts'),
    #         'rental.contract',
    #         [('building_id', '=', self.id)],
    #         {'default_building_id': self.id},
    #     )

    def action_create_units(self):
        property_pool = self.env['product.template']
        floor_pool = self.env['re.floor']
        props = []
        if self.no_of_floors and self.props_per_floors:
            if not self.code:
                raise ValidationError(_("Building code is not set. Please set a valid code for the building."))
            i = 1
            while i <= self.no_of_floors:
                floor_rec = floor_pool.search(
                    [('building_id', '=', self.id), ('level_number', '=', i)],
                    limit=1,
                )
                if not floor_rec:
                    floor_rec = floor_pool.create({
                        'name': f'Floor {i}',
                        'code': f'{self.code}/F{i:03d}',
                        'building_id': self.id,
                        'company_id': self.company_id.id,
                        'level_number': i,
                        'sequence': i,
                    })
                j = 1
                while j <= self.props_per_floors:
                    vals = {
                        'name': self.code + ' / F' + str(i).zfill(3) + ' / U' + str(j).zfill(3),
                        'code': self.code + '/F' + str(i).zfill(3) + '/U' + str(j).zfill(3),
                        'block_id': self.block_id.id,
                        'building_id': self.id,
                        'floor': str(i),
                        'floor_id': floor_rec.id,
                        'is_property': True,
                        'deposit': 0,
                        'building_status_id': self.building_status_id.id,
                        'gross_area': self.gross_area,
                        'building_type_id': self.building_type_id.id,
                        'building_status_id': self.building_status_id.id,
                        'site_id': self.site_id.id,
                    }
                    prop_id = property_pool.create(vals)
                    props.append(prop_id.id)
                    j += 1
                i += 1
            self.unit_ids = [(6, 0, props)]
        else:
            raise ValidationError(
                _("Please set valid numbers for the number of floors and units per floor.")
            )

    # def write(self, vals):
    #     res = super(Building, self).write(vals)
    #     if 'stage_id' in vals:
    #         for rec in self:
    #             if rec.stage_id:
    #                 lines = self.env['loan.line.rs.own'].search([
    #                     ('eligibility_state', 'in', ('pending', 'eligible')),
    #                     ('trigger_level', '=', 'building'),
    #                     ('paid', '=', False),
    #                     ('progress_building_stage_id', '=', rec.stage_id.id),
    #                     '|',
    #                     ('loan_id.building_id', '=', rec.id),
    #                     ('loan_id.building_unit_id.building_id', '=', rec.id),
    #                 ])
    #                 lines._notify_on_stage_match()
    #     return res

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            self.env['loan.line.rs.own'].process_stage_change_notifications(
                trigger_level='building',
                records=self,)
        return res
