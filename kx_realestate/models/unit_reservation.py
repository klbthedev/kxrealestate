import calendar
from datetime import datetime, date, timedelta
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError

class UnitReservation(models.Model):
    _name = "unit.reservation"
    _description = "Property Reservation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    account_id = fields.Many2one('account.account', string='Income Account')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    address = fields.Char(string='Address')
    building_id = fields.Many2one('building.building', related="building_unit_id.building_id", string='Building')
    floor_id = fields.Many2one('re.floor', related="building_unit_id.floor_id", string='Floor')
    building_code = fields.Char(string='Code')
    building_status_id = fields.Many2one('building.status', string='Building Unit Status')
    building_unit_id = fields.Many2one('product.template', string='Unit', required=False)
    site_id = fields.Many2one('re.site', string='Site', related='building_unit_id.site_id', store=True, readonly=True)
    block_id = fields.Many2one('re.block', string='Block', related='building_unit_id.block_id', store=True, readonly=True)
    building_unit_area = fields.Integer(string='Building Unit Area m²')
    building_type_id = fields.Many2one('building.type', string='Building Unit Type')
    contract_count_own = fields.Integer(string='Sales', compute='_contract_count_own')
    # contract_count_rent = fields.Integer(string='Rentals', compute='_contract_count_rent')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    date = fields.Datetime(string='Reservation Date', default=fields.Datetime.now)
    exp_date = fields.Datetime(string='Reservation Expiry Date', )
    deposit = fields.Float(string='Deposit', digits=(16, 2))
    deposit_count = fields.Integer(string='Deposits', compute='_deposit_count')
    deposit_remaining_amount = fields.Integer(string="Remaining Deposit", compute="_compute_deposit_remaining_amount")
    first_payment_date = fields.Date(string='First Payment Date')
    floor = fields.Char(string='Floor')
    installment_template_id = fields.Many2one('installment.template', string='Payment Template')
    loan_line_rs_ids = fields.One2many('loan.line.rs', 'loan_id')
    name = fields.Char(string='Name', readonly=True)
    ownership_contract_id = fields.Many2one('ownership.contract', string='Ownership Contract')
    partner_id = fields.Many2one('res.partner', string='Customer')
    # region_id = fields.Many2one('regions.regions', string='Region', related='building_id.region_id', store=True, readonly=True)
    selling_price = fields.Integer(string="Pricing")
    state = fields.Selection([('draft','Draft'),
                             ('confirmed','Confirmed'),
                             ('contracted','Contracted'),
                             ('canceled','Canceled')
    ], string='State', compute='_compute_state', store=True, readonly=False, default='draft')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    unit_code = fields.Char(string='Code')

    def _contract_count_own(self):
        own_obj = self.env['ownership.contract']
        own_ids = own_obj.search([('reservation_id', '=', self.id)])
        self.contract_count_own = len(own_ids)

    @api.model
    def check_and_cancel_expired_reservations(self):
        now = fields.Datetime.now()
        expired_reservations = self.search([
            ('exp_date', '<', now),
            ('state', 'in', ['draft', 'confirmed']) 
        ])
        if expired_reservations:
            expired_reservations.write({'state': 'canceled'})
    @api.depends('exp_date')
    def _compute_state(self):
        now = fields.Datetime.now()
        for record in self:
            if record.exp_date and record.exp_date < now and record.state not in ['contracted', 'canceled']:
                record.state = 'canceled'
            elif not record.state:
                record.state = 'draft'
    
    def _deposit_count(self):
        payment_obj = self.env['account.payment']
        for rec in self:
            actual_id = rec._origin.id if rec._origin else rec.id
            if not actual_id or isinstance(actual_id, models.NewId):
                rec.deposit_count = 0
                continue
            payment_ids = payment_obj.search([
                ('reservation_id', '=', actual_id),
                ('state', 'not in', ['cancel'])
            ])
            rec.deposit_count = len(payment_ids)
    
    @api.depends('deposit') 
    def _compute_deposit_remaining_amount(self):
        payment_obj = self.env['account.payment']
        for rec in self:
            actual_id = rec._origin.id if rec._origin else rec.id
            if not actual_id or isinstance(actual_id, models.NewId):
                rec.deposit_remaining_amount = rec.deposit
                continue
            payment_ids = payment_obj.search([
                ('reservation_id', '=', actual_id),
                ('state', 'not in', ['cancel']) 
            ])
            paid_amount = sum(payment.amount for payment in payment_ids)
            rec.deposit_remaining_amount = max(0.0, rec.deposit - paid_amount)

    def unlink(self):
        if self.state != 'draft':
            raise UserError(_('You can not delete a reservation not in draft state'))
        super(UnitReservation, self).unlink()

    _sql_constraints = [('name_uniq', 'unique(name)', 'Reservation Number record must be unique !')]

    def auto_cancel_reservation(self):
        try:
            reservation_pool = self.env['unit.reservation']
            params = self.env['ir.config_parameter'].sudo()
            reservation_hours = int(
                params.get_param('kx_real_estate.reservation_hours')
                or params.get_param('kx_realestate.reservation_hours')
                or params.get_param('reservation_hours')
                or 0
            )
            if not reservation_hours:
                return True
            timeout_reservation_ids = reservation_pool.search([('state','=','confirmed'),('date','<=',str(datetime.now() - timedelta(hours=reservation_hours)))])
            for reservation in timeout_reservation_ids:
                reservation.write({'state': 'canceled'})
                unit = reservation.building_unit_id
                unit.write({'state': 'free'})
        except:
            return "internal error"

    @api.onchange('building_unit_id')
    def onchange_unit(self):
        unit = self.building_unit_id
        if not unit:
            return
        self.unit_code = unit.code
        self.floor = unit.floor
        self.building_type_id = unit.building_type_id
        self.address = unit.address
        self.building_status_id = unit.building_status_id
        self.building_unit_area = unit.building_unit_area
        self.building_id = unit.building_id.id

    @api.onchange('building_id')
    def onchange_building(self):
        if self.building_id:
            units = self.env['product.template'].search([('is_property', '=', True),('building_id', '=', self.building_id.id),('state','=','free')])
            unit_ids=[]
            for u in units: unit_ids.append(u.id)
            building_obj = self.env['building.building'].browse(self.building_id.id)
            code = building_obj.code
            no_of_floors = building_obj.no_of_floors
            analytic_account_id = building_obj.analytic_account_id.id
            if building_obj:
                vals = {
                    'building_code': code,
                    'analytic_account_id': analytic_account_id,
                    'no_of_floors': no_of_floors,
                }
                domain = {
                    'building_unit_id': [('id', 'in', unit_ids)]
                }
                return {
                    'value': vals,
                    'domain': domain,
                }

    def action_draft(self):
        self.write({'state':'draft'})

    def action_cancel(self):
        self.write({'state':'canceled'})
        unit = self.building_unit_id
        unit.write({'state':  'free'})

    def unit_status(self):
        return self.building_unit_id.state

    def action_confirm(self):
        for record in self:
            if not record.deposit >= record.building_unit_id.deposit:
                raise ValidationError("Add valid deposit for deside unit")
            record.write({'state':'confirmed'})
            unit = record.building_unit_id
            unit.write({'state': 'reserved'})

    def action_receive_deposit(self):
        self.ensure_one()
        if self.deposit_remaining_amount <= 0:
            raise UserError(_('The deposit for this reservation has already been fully paid!'))
        return {
            'name': _('Payment'),
            'view_mode': 'form',
            'res_model': 'account.payment',
            'view_id': self.env.ref('account.view_account_payment_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'form_view_initial_mode': 'edit',
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_amount': self.deposit_remaining_amount, 
                'default_partner_id': self.partner_id.id,
                'default_reservation_id': self.id,
            },
            'target': 'current'
        }

    def view_deposits(self):
        payment_obj = self.env['account.payment']
        payment_ids = payment_obj.search([('reservation_id', '=', self.id)])
        return {
            'name': _('Payments'),
            'domain': [('id', 'in', payment_ids.ids)],
            'view_mode': 'list,form', 
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_contract_ownership(self):
        existing_contract = self.env['ownership.contract'].search([
            ('reservation_id', '=', self.id),
            ('state', '!=', 'cancel')
        ], limit=1)
        if existing_contract:
            raise UserError(_('An active ownership contract already exists for this reservation.'))
        return {
            'name': _('Ownership Contract'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ownership.contract',
            'view_id': self.env.ref('kx_realestate.ownership_contract_form_view').id,
            'type': 'ir.actions.act_window',
            'context': {
                'form_view_initial_mode': 'edit',
                'default_building_id': self.building_id.id,
                # 'default_region_id': self.region_id.id,
                'default_building_code': self.building_code,
                'default_partner_id': self.partner_id.id,
                'default_building_unit_id': self.building_unit_id.id,
                'default_unit_code': self.unit_code,
                'default_floor': self.floor,
                'default_building_type_id': self.building_type_id.id,
                'default_building_status_id': self.building_status_id.id,
                'default_building_unit_area': self.building_unit_area,
                'default_reservation_id': self.id,
            },
            'target': 'current'
        }

    def action_mark_contracted(self):
        for rec in self:
            unit = rec.building_unit_id
            unit.write({'state' : 'sold'})
            rec.write({'state' : 'contracted'})

    def action_contract_ownership_resell(self):
        self.ownership_contract_id.state = 'resell'
        return {
            'name': _('Ownership Contract'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ownership.contract',
            'view_id': self.env.ref('kx_realestate.ownership_contract_form_view').id,
            'type': 'ir.actions.act_window',
            'context': {
                'form_view_initial_mode': 'edit',
                'default_building_id': self.building_id.id,
                # 'default_region_id': self.region_id.id,
                'default_building_code': self.building_code,
                'default_partner_id': self.partner_id.id,
                'default_building_unit_id': self.building_unit_id.id,
                'default_unit_code': self.unit_code,
                'default_floor': self.floor,
                'default_building_type_id': self.building_type_id.id,
                'default_building_status_id': self.building_status_id.id,
                'default_building_unit_area': self.building_unit_area,
                'default_reservation_id': self.id,
            },
            'target': 'current'
        }

    # def action_contract_rental(self):
    #     return {
    #         'name': _('Rental Contract'),
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'rental.contract',
    #         'view_id': self.env.ref('kx_realestate.rental_contract_form_view').id,
    #         'type': 'ir.actions.act_window',
    #         'context': {
    #             'form_view_initial_mode': 'edit',
    #             'default_building': self.building_id.id,
    #             'default_region_id': self.region_id.id,
    #             'default_building_code': self.building_code,
    #             'default_partner_id': self.partner_id.id,
    #             'default_building_unit_id': self.building_unit_id.id,
    #             'default_unit_code': self.unit_code,
    #             'default_floor': self.floor,
    #             'default_building_type_id': self.building_type_id.id,
    #             'default_building_status_id': self.building_status_id.id,
    #             'default_building_unit_area': self.building_unit_area,
    #             'default_reservation_id': self.id,
    #         },
    #         'target': 'current'
    #     }

    def view_contract_own(self):
        own_obj = self.env['ownership.contract']
        own_ids = own_obj.search([('reservation_id', '=', self.id)])
        return {
            'name': _('Ownership Contract'),
            'domain': [('id', 'in', own_ids.ids)],
            'view_type':'form',
            'view_mode':'list,form',
            'res_model':'ownership.contract',
            'type':'ir.actions.act_window',
            'nodestroy':True,
            'view_id': False,
            'target':'current',
        }

    # def view_contract_rent(self):
    #     rent_obj = self.env['rental.contract']
    #     rent_ids = rent_obj.search([('reservation_id', '=', self.id)])
    #     return {
    #         'name': _('Rental Contract'),
    #         'domain': [('id', 'in', rent_ids.ids)],
    #         'view_type': 'form',
    #         'view_mode': 'list,form',
    #         'res_model': 'rental.contract',
    #         'type': 'ir.actions.act_window',
    #         'nodestroy': True,
    #         'view_id': False,
    #         'target': 'current',
    #     }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('unit.reservation')
        new_id = super(UnitReservation, self).create(vals)
        return new_id

    def add_months(self,sourcedate,months):
        month = sourcedate.month - 1 + months
        year = int(sourcedate.year + month / 12 )
        month = month % 12 + 1
        day = min(sourcedate.day,calendar.monthrange(year,month)[1])
        return date(year,month,day)

    def _prepare_lines(self,first_date):
        loan_lines=[]
        if self.installment_template_id:
            selling_price = self.selling_price
            mon = self.installment_template_id.month
            yr = self.installment_template_id.duration_year
            repetition = self.installment_template_id.repetition_rate
            advance_percent = self.installment_template_id.advance_payment
            deducted_amount = self.installment_template_id.deducted_amount
            if not first_date:
                raise UserError(_('Please select first payment date!'))
            adv_payment=selling_price*float(advance_percent)/100
            if mon>12:
                x = mon/12
                mon=(x*12)+mon%12
            mons=mon+(yr*12)
            if adv_payment:
                loan_lines.append((0,0,{'amount':adv_payment,'date': first_date, 'name':_('Advance Payment')}))
                if deducted_amount:
                    selling_price-=adv_payment
            loan_amount=(selling_price/float(mons))*repetition
            m=0
            i=2
            while m<mons:
                loan_lines.append((0,0,{'amount':loan_amount,'date': first_date,'name':_('Loan Installment')}))
                i+=1
                first_date = self.add_months(first_date, repetition)
                m+=repetition
        return loan_lines
