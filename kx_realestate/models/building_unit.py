from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class RealEstateUnitStatus(models.Model):
    _name = "re.unit.status"
    _description = "Real Estate Unit Status"

    unit_id = fields.Many2one(
        'product.template',
        string='Building',
        ondelete='cascade'
    )
    floor_id = fields.Many2one(
        're.floor',
        related='unit_id.floor_id',
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
        related='unit_id.building_type_id',
        store=True,
        readonly=True
    )
    unit_status_id_date = fields.Datetime(default=fields.Datetime.now)
    unit_status_id = fields.Many2one(
        're.unit.stage',
        string="Unit Stage",
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


class BuildingUnit(models.Model):
    _inherit = 'product.template'
    _description = "Product Template"

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

    @api.model_create_multi
    def create(self, vals_list):
        # Ensure records created from real-estate flows always become units.
        for vals in vals_list:
            if (
                vals.get('is_property')
                or vals.get('building_id')
                or vals.get('floor_id')
                or self.env.context.get('default_is_property')
                or self.env.context.get('default_building_id')
                or self.env.context.get('default_floor_id')
            ):
                vals['is_property'] = True
            
            # Hierarchical sequence for units
            if vals.get('is_property') and (not vals.get('code') or vals.get('code') == '/'):
                floor = self.env['re.floor'].browse(vals.get('floor_id'))
                prefix = floor.code + '/' if floor and floor.code else ''
                vals['code'] = prefix + (self.env['ir.sequence'].next_by_code('re.unit') or '/')

            if vals.get('is_property') and not vals.get('stage_id') and vals.get('building_type_id'):
                stage = self.env['re.unit.stage'].search([
                    ('active', '=', True),
                    '|',
                    ('building_type_id', '=', False),
                    ('building_type_id', '=', vals['building_type_id'])
                ], order='sequence asc', limit=1)
                if stage:
                    vals['stage_id'] = stage.id
        return super().create(vals_list)

    unit_status_ids = fields.One2many('re.unit.status','unit_id', string='Unit status')
    
    active = fields.Boolean(string='Active', default=True,
        help="If the active field is set to False, it will allow you to hide the top without removing it.")
    air_condition = fields.Selection([('unknown','Unknown'),
                                    ('central','Central'),
                                    ('partial','Partial'),
                                    ('none', 'None'),
                                    ], string="Air Condition")
    amenity_ids = fields.Many2many('re.amenity', 'unit_amenity_rel', 'unit_id', 'amenity_id', string='Amenities')
    address = fields.Char(string='Address')
    building_attachment_line_ids = fields.One2many("unit.attachment.line", "product_attach_id", string="Documents")
    block_id = fields.Many2one('re.block', string='Block', related='building_id.block_id', store=True, readonly=True)
    building_id = fields.Many2one('building.building', string='Building', ondelete='cascade')
    balcony = fields.Float(string='Balconies m²')
    bathrooms = fields.Integer(string='Bathrooms')
    building_unit_area = fields.Float(string='Building Unit Area m²')
    building_net_area = fields.Float(string='Net Area m²')
    building_type_id = fields.Many2one('building.type', string='Building Unit Type')
    parent_building_address = fields.Char(related='building_id.address', string='Parent Building Address', readonly=True)
    parent_title_deed_no = fields.Char(
        related='building_id.title_deed_no',
        string='Parent Title Deed / Ownership Certificate No.',
        readonly=True,
    )
    parent_title_deed_date = fields.Date(related='building_id.title_deed_date', string='Parent Title Deed Date', readonly=True)
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    # components_line_ids = fields.One2many('components.line', 'unit_id', string='Components List')
    count = fields.Integer(string='Count', default=1)
    construction_date = fields.Date(string='Construction Date')
    category = fields.Char(string='Category', size=16)
    code = fields.Char(string='Code', readonly=True)
    description = fields.Text(string='Description')
    building_description_id = fields.Many2one('building.description', string='Description')
    building_status_id = fields.Many2one('building.status', string='Unit Status')
    date_added = fields.Date(string='Date Added to Notarization')
    deposit = fields.Float(string='Deposit')
    electricity_meter = fields.Char(string='Electricity meter', size=16)
    east = fields.Char(string='Eastern border by')
    floor = fields.Char(string='Floor', size=16)
    floor_id = fields.Many2one('re.floor', string='Floor', ondelete='restrict')
    garden = fields.Integer(string='Garden m²')
    garage_included = fields.Integer(string='Garage included')
    handicap_accessible = fields.Boolean(string='Handicap Accessible')
    heating = fields.Selection([('unknown','unknown'),
                                ('none','none'),
                                ('tiled_stove', 'tiled stove'),
                                ('stove', 'stove'),
                                ('central','central heating'),
                                ('self_contained_central','self-contained central heating')], string="Heating")
    heating_source = fields.Selection([('unknown','unknown'),
                                        ('electricity','Electricity'),
                                        ('wood','Wood'),
                                        ('pellets','Pellets'),
                                        ('oil','Oil'),
                                        ('gas','Gas'),
                                        ('district','District Heating')], string="Heating Source")
    is_property = fields.Boolean(string='Property')
    internet = fields.Boolean(string='Internet')
    insurance_fee = fields.Integer(string='Insurance fee')
    longitude = fields.Float(string='Longitude')
    latitude = fields.Float(string='Latitude')
    gross_area = fields.Float(string='Gross Area m²')
    target_lease = fields.Integer(string='Target Lease')
    passenger_lift = fields.Integer(string='Passenger Elevators')
    freight_lift = fields.Integer(string='Freight Elevators')
    license_code = fields.Char(string='License Code', size=16)
    license_date = fields.Date(string='License Date')
    license_location = fields.Char(string='License Notarization')
    name = fields.Char(string='Name', required=True)
    note = fields.Html(string='Notes')
    north = fields.Char(string='Northen border by')
    old_building = fields.Boolean(string='Old Building')
    selling_price = fields.Float(string='Selling Price')
    parking_place_rentable = fields.Boolean(string='Parking rentable')
    partner_id = fields.Many2one('res.partner', string='Owner')
    sale_date = fields.Date(string='Sale Date')
    property_image_ids = fields.One2many('property.image', 'product_tmplate_id', string="Extra Product Media", copy=True)
    # region_id = fields.Many2one('regions.regions', string='Region', related='building_id.region_id', store=True, readonly=True)
    reservation_ids = fields.One2many('unit.reservation', 'building_unit_id', string='Reservations')
    ownership_contract_ids = fields.One2many('ownership.contract', 'building_unit_id', string='Ownership contracts')
    # rental_contract_ids = fields.One2many('rental.contract', 'building_unit_id', string='Rental contracts')
    reservation_count = fields.Integer(compute='_compute_unit_contract_stats', string='Reservations')
    ownership_contract_count = fields.Integer(compute='_compute_unit_contract_stats', string='Sales')
    # rental_contract_count = fields.Integer(compute='_compute_unit_contract_stats', string='Rentals')
    rooms = fields.Integer(string='Rooms')
    rental_fee = fields.Integer(string='Rental fee')
    solar_electric = fields.Boolean(string='Solar Electric System')
    solar_heating = fields.Boolean(string='Solar Heating System')
    staircase = fields.Char(string='Staircase', size=8)
    stock_state = fields.Selection([
                            ('raw_material', 'Raw Material'),
                            ('wip', 'Work in Progress'),
                            ('semi_finished', 'Semi-finished'),
                            ('finished', 'Finished'),
                            ('sold', 'Sold'),
                            ('leased', 'Leased'),
                            ('blocked', 'Blocked'),
                        ], string='Construction Stock State', default='raw_material', tracking=True)
    surface = fields.Integer(string='Surface')
    sort = fields.Integer(string='Sort')
    sequence = fields.Integer(string='Sequence')
    south = fields.Char(string='Southern border by')
    stage_id = fields.Many2one(
        're.unit.stage',
        string="Unit Stage",
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
    site_id = fields.Many2one('re.site', string='Site', related='building_id.site_id', store=True, readonly=True)
    state= fields.Selection([('free','Available'),
                            ('reserved','Reserved'),
                            ('sold','Sold'),
                            # ('on_lease','Rent'),
                            ('blocked','Blocked')], string='State', default='free')
    terraces = fields.Integer(string='Terraces m²')
    telephon = fields.Boolean(string='Telephone')
    installment_template_id = fields.Many2one('installment.template', string='Payment Template')
    url = fields.Char(string='Website URL')
    usage = fields.Selection([('unlimited','unlimited'),
                            ('office','Office'),
                            ('shop','Shop'),
                            ('flat','Flat'),
                            ('rural','Rural Property'),
                            ('parking','Parking')], string='Usage')
    video_url = fields.Char(string='Vidoe URL')
    website_published = fields.Boolean(string='Website Published', default=True)
    water_meter = fields.Char(string='Water meter', size=16)
    west = fields.Char(string='Western border by')
    # furniture = fields.Boolean(string='Furniture')

    _sql_constraints = [
        # ('unique_property_code', 'UNIQUE (code,building_id,region_id)', 'property code must be unique!'),
        ('unique_property_building_code', 'UNIQUE (code,building_id)', 'property code must be unique!'),
    ]

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        for unit in self:
            if unit.floor_id:
                unit.floor = str(unit.floor_id.level_number)
                unit.building_id = unit.floor_id.building_id.id

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
        return self.env['re.unit.stage'].search(stage_domain, order='sequence, id')

    @api.onchange('building_type_id')
    def _onchange_building_type_id_stage(self):
        for unit in self:
            if unit.building_type_id:
                stages = self.env['re.unit.stage'].search([
                    ('active', '=', True),
                    '|',
                    ('building_type_id', '=', False),
                    ('building_type_id', '=', unit.building_type_id.id)
                ], order='sequence asc', limit=1)
                if stages:
                    unit.stage_id = stages.id

    @api.depends('stage_id', 'building_type_id')
    def _compute_progress_percent(self):
        for rec in self:
            stages = self.env['re.unit.stage'].search([
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

    @api.depends('reservation_ids', 'ownership_contract_ids')
    def _compute_unit_contract_stats(self):
        for unit in self:
            unit.reservation_count = len(unit.reservation_ids)
            unit.ownership_contract_count = len(unit.ownership_contract_ids)
            # unit.rental_contract_count = len(unit.rental_contract_ids)

    def view_reservations(self):
        self.ensure_one()
        return {
            'name': _('Reservations'),
            'type': 'ir.actions.act_window',
            'res_model': 'unit.reservation',
            'view_mode': 'list,form',
            'domain': [('building_unit_id', '=', self.id)],
            'context': {'default_building_unit_id': self.id},
            'target': 'current',
        }

    def view_ownership_contracts(self):
        self.ensure_one()
        return {
            'name': _('Ownership contracts'),
            'type': 'ir.actions.act_window',
            'res_model': 'ownership.contract',
            'view_mode': 'list,form',
            'domain': [('building_unit_id', '=', self.id)],
            'context': {'default_building_unit_id': self.id},
            'target': 'current',
        }


    def make_reservation(self):
        for unit_obj in self:
            if not unit_obj.deposit >= 100:
                raise UserError("Add deposit must be grater than 100 to make a reservation..")
            vals = {
                'unit_code' : unit_obj.code,
                'building_unit_id' : unit_obj.id,
                'address' : unit_obj.address,
                'floor' : unit_obj.floor,
                'selling_price' : unit_obj.selling_price,
                'building_type_id' : unit_obj.building_type_id.id,
                'building_status_id' : unit_obj.building_status_id.id,
                'building_id' : unit_obj.building_id.id,
                'building_code' : unit_obj.building_id.code,
                # 'region_id' : unit_obj.region_id.id,
                'building_unit_area' : unit_obj.building_unit_area,
                'deposit' : unit_obj.deposit,
                }
            self.state = "reserved"
            reservation = self.env['unit.reservation']
            reservation_id = reservation.create(vals)
            return {
                'view_type':'form',
                'view_mode':'form',
                'res_model':'unit.reservation',
                'type':'ir.actions.act_window',
                'nodestroy':True,
                'target':'current',
                'res_id': reservation_id.id,
            }

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            self.env['loan.line.rs.own'].process_stage_change_notifications(
                trigger_level='unit',
                records=self,)
        return res
