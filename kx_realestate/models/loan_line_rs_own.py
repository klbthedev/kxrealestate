from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import requests
import logging
_logger = logging.getLogger(__name__)


class AmountPayment(models.Model):
    _inherit = 'account.payment'

    collected_month = fields.Char(
        string="Collected Month",
        compute="_compute_collected_month",
        store=True
    )

    loan_line_rs_own_id = fields.Many2one('loan.line.rs.own')

    @api.depends('date')
    def _compute_collected_month(self):
        for rec in self:
            rec.collected_month = rec.date.strftime('%Y-%m') if rec.date else False

class LoanLineRsOwn(models.Model):
    _name = 'loan.line.rs.own'
    _order = 'date, name'

    amount = fields.Float(string='Payment', digits='Product Price', group_operator="sum")
    original_amount = fields.Float(string='Original Amount', readonly=True)
    discount_percent = fields.Float(string='Discount (%)')
    amount_residual = fields.Float(compute='_compute_amount_tracking', string='Balance', readonly=True, store=True, group_operator="sum")
    amount_type = fields.Selection([('fixed', 'Fixed'), ('percent', 'Percent')], default='fixed', required=True)
    amount_value = fields.Float(string='Configured Amount/Percent')
    auto_invoice = fields.Boolean(string='Auto Draft Invoice', default=True)
    cancelled = fields.Boolean(string='Cancelled')
    contract_user_id = fields.Many2one(string='User', related= 'loan_id.user_id', store=True)
    contract_partner_id = fields.Many2one(string='Partner', related= 'loan_id.partner_id', store=True)
    contract_building_id = fields.Many2one(string="Building", related='loan_id.building_id', store=True)
    contract_building_unit_id = fields.Many2one(related='loan_id.building_unit_id',string="Building Unit", store=True,domain=[('is_property', '=', True)])
    # contract_region_id = fields.Many2one(related='loan_id.region_id',string="Region", store=True)
    currency_id = fields.Many2one('res.currency', related='loan_id.company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True,  default=lambda self: self.env.user.company_id.id)
    
    selected_floor_id = fields.Many2one('re.floor', string="Floor #", store=True)
    
    date = fields.Date(string='Due Date')
    month = fields.Char(compute="_compute_month",store=True)
    year = fields.Char(compute="_compute_month",store=True)
    @api.depends('date')
    def _compute_month(self):
        for rec in self:
            if rec.date:
                rec.month = rec.date.strftime('%B')
                rec.year = str(rec.date.year)
            else:
                rec.month = False
                rec.year = False
    
    eligibility_state = fields.Selection(
        [('pending', 'Pending'), ('eligible', 'Eligible'), ('invoiced', 'Invoiced'), ('paid', 'Paid')],
        default='pending',
        string='Eligibility',
        tracking=True,
    )
    trigger_level = fields.Selection(
        [('building', 'Building'), ('floor', 'Floor'), ('unit', 'Unit')],
        string='Trigger Level',
        # required=True,
    )
    trigger_building_type_id = fields.Many2one('building.type', compute='_compute_trigger_building_type_id')

    @api.depends('loan_id.building_id.building_type_id', 'loan_id.building_unit_id.building_type_id', 'loan_id.building_type_id')
    def _compute_trigger_building_type_id(self):
        for rec in self:
            building_type = False
            if rec.loan_id.building_id:
                building_type = rec.loan_id.building_id.building_type_id
            elif rec.loan_id.building_unit_id:
                building_type = rec.loan_id.building_unit_id.building_type_id
            elif rec.loan_id.building_type_id:
                building_type = rec.loan_id.building_type_id
            rec.trigger_building_type_id = building_type.id if building_type else False

    progress_building_stage_id = fields.Many2one(
        're.building.stage',
        string='Required Stage',
        domain="[('active', '=', True), '|', ('building_type_id', '=', False), ('building_type_id', '=', trigger_building_type_id)]",
    )
    progress_floor_stage_id = fields.Many2one(
        're.floor.stage',
        string='Required Stage',
        domain="[('active', '=', True), '|', ('building_type_id', '=', False), ('building_type_id', '=', trigger_building_type_id)]",
    )
    progress_unit_stage_id = fields.Many2one(
        're.unit.stage',
        string='Required Stage',
        domain="[('active', '=', True), '|', ('building_type_id', '=', False), ('building_type_id', '=', trigger_building_type_id)]",
    )
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_state = fields.Selection(related='invoice_id.state', readonly=True,)
    last_eligibility_check = fields.Datetime(readonly=True)
    loan_id = fields.Many2one('ownership.contract', string='',ondelete='cascade', readonly=True)
    name = fields.Char(string='Name')
    
    number = fields.Char(string='Number', required=True,)
    _sql_constraints = [('unique_number_per_contract', 'UNIQUE(loan_id, number)', 'Installment number must be unique within this contract.')]
    
    
    
    
    # property_code = fields.Char(
    #     string='Property Code',
    #     required=True,
    # )   



    trigger_type = fields.Selection(
        [
            ('date', 'Date'),
            ('construction', 'Construction'),
        ],
        default='date',
        string='Trigger Type',
        required=True,
    )
    payment_count = fields.Integer(compute='_count_payment', string='Counts')
    progress_percent = fields.Float(string='Required Progress %')
    finance_means = fields.Selection([('self_finance','Self Finance'),('bank','Bank')], default='self_finance', required=True,)
    payment_state = fields.Selection(related='invoice_id.payment_state', readonly=True, store=True)
    paid = fields.Boolean(compute='_compute_amount_tracking', store=True, string='Paid', readonly=True)
    reminder_last_date = fields.Date(string='Last Reminder On')
    notification_frequency = fields.Selection(
        [
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='weekly',
        string='Notification Frequency',
        tracking=True,   )

    last_stage_notification_date = fields.Date(string='Last Stage Notification')
    reminder_state = fields.Selection(
        [('none', 'None'), ('upcoming', 'Upcoming'), ('due', 'Due'), ('overdue', 'Overdue')],
        default='none',
        string='Reminder Status',
        tracking=True,
    )

    installment_count = fields.Integer(default=1, readonly=True, store=True)
    payment_bucket = fields.Selection([
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
    ], compute="_compute_payment_bucket", store=True)
    building_unit_id = fields.Many2one('building.unit', string="Building Unit")

    @api.depends('paid')
    def _compute_payment_bucket(self):
        for rec in self:
            rec.payment_bucket = 'paid' if rec.paid else 'unpaid'

    collected_month = fields.Char(
        string="Collected Month",
        compute="_compute_collected_month",
        store=True
    )
    collected_amount = fields.Float(
        string="Collected Line Amount",
        compute="_compute_collected_month",
        store=True
    )
    @api.depends('invoice_id.payment_state', 'invoice_id')
    def _compute_collected_month(self):
        Payment = self.env['account.payment']
        for rec in self:
            payments = Payment.search([
                ('loan_line_rs_own_id', '=', rec.id),
                ('state', '=', 'posted')
            ])
            rec.collected_amount = sum(payments.mapped('amount'))
            if payments:
                latest_date = max(payments.mapped('date'))
                rec.collected_month = latest_date.strftime('%Y-%m')
            else:
                rec.collected_month = False

    #######################################################################################################
    # installment validation rule for trigger_type 'construction'
    
    @api.constrains('trigger_type', 'trigger_level')
    def _check_trigger_level(self):
        for rec in self:
            if rec.trigger_type == 'construction':
                if rec.trigger_level == 'building' and not rec.progress_building_stage_id:
                    raise ValidationError("Please set Building Stage. You can not leave Building Stage empty.")
                if rec.trigger_level == 'floor' and not rec.progress_floor_stage_id:
                    raise ValidationError("Please set Floor Stage. You can not leave Floor Stage empty.")
                if rec.trigger_level == 'unit' and not rec.progress_unit_stage_id:
                    raise ValidationError("Please set Unit Stage. You can not leave Unit Stage empty.")
    
    #######################################################################################################
    # update installment due date field when payment_term_date field is chanaged    
    @api.onchange('payment_term_date', 'status_complete_date')
    def _onchange_dates(self):
        for rec in self:
            if rec.payment_term_date and rec.status_complete_date:
                rec.date = rec.status_complete_date + timedelta(days=rec.payment_term_date)

    # @api.constrains('payment_term_date')
    # def _check_payment_term_date(self):
    #     for rec in self:
    #         rec.date = rec.status_complete_date + timedelta(days=rec.payment_term_date or 0)        
    #######################################################################################################
    
    # def write(self, vals):
    #     for rec in self:
    #         date = vals.get('date', rec.date)
    #         trigger_level = vals.get('trigger_level', rec.trigger_level)

    #         if not date and not trigger_level:
    #             raise ValidationError("Update Error: Please set either due date or trigger level.")

    #         if date and trigger_level:
    #             raise ValidationError("Update Error: Please set either due date or trigger level, not both.")

    #     res = super().write(vals)

    #     for rec in self:
    #         if rec.status_complete_date:
    #             base_date = rec.status_complete_date.date()

    #             super(LoanLineRsOwn, rec).write({
    #                 'date': base_date + timedelta(days=int(self.payment_term_date or 0))
    #             })

    #     return res

    #######################################################################################################

    status = fields.Char(string='Status')
    total_paid_amount = fields.Float(
        string='Collected Amount',
        compute='_compute_paid_amount_simple',
        store=True,
        group_operator='sum',
    )

    total_remaining_amount = fields.Float(compute='_compute_amount_tracking',store=True, string='Remaining Amount', readonly=True)
    trigger_date = fields.Date(string='Trigger Date')
    # trigger_type = fields.Selection(
    #     [('date', 'Date'), ('progress', 'Progress'), ('manual', 'Manual'), ('mixed', 'Mixed')],
    #     default='date',
    #     required=True,
    #     string='Trigger Type',
    #     tracking=True,
    # )
    payment_term_date_id = fields.Many2one('payment.term.config', string='Payment Term Date')
    payment_term_date = fields.Integer(related="payment_term_date_id.payment_term_date", string='Payment Term Date', default=0,)
    payment_request_letter = fields.Selection([('yes','Yes'),('no','No')], string='Payment Request Letter', default='no',required=True)
    status_complete_date = fields.Date(store=True,)

    report_building_id = fields.Many2one(
        'building.building',
        string='Building',
        related='loan_id.building_id',
        store=True,
        readonly=True,
        index=True,
    )

    report_floor_id = fields.Many2one(
        're.floor',
        string='Floor',
        related='loan_id.floor_id',
        store=True,
        readonly=True,
        index=True,
    )

    report_unit_id = fields.Many2one(
        'product.template',
        string='Unit',
        related='loan_id.building_unit_id',
        store=True,
        readonly=True,
        index=True,
    )

    total_amount_report = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount_report',
        store=True,
        group_operator='sum',
    )

    @api.depends('amount')
    def _compute_total_amount_report(self):
        for rec in self:
            rec.total_amount_report = rec.amount or 0.0    

    def view_payments(self):
        payments = self.env['account.payment'].sudo().search([('loan_line_rs_own_id','=',self.id)]).ids
        return {
            'name': _('Vouchers'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments)],
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }

    def action_open_ownership_contract(self):
        self.ensure_one()
        if not self.loan_id:
            return False
        return {
            'name': _('Ownership contract'),
            'type': 'ir.actions.act_window',
            'res_model': 'ownership.contract',
            'view_mode': 'form',
            'res_id': self.loan_id.id,
            'target': 'current',
        }

    def action_open_installment_payment_wizard(self):
        self.ensure_one()
        return {
            'name': _('Installment Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'installment.payment.check',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'loan.line.rs.own',
                'active_id': self.id,
            },
        }

    def _count_payment(self):
        for rec in self:
            payments = self.env['account.payment'].sudo().search([('loan_line_rs_own_id','=',rec.id)]).ids
            rec.payment_count = len(payments)

    @api.depends('amount', 'invoice_id.amount_residual')
    def _compute_amount_tracking(self):
        for rec in self:
            if rec.invoice_id:
                rec.amount_residual = rec.invoice_id.amount_residual
            else:
                rec.amount_residual = rec.amount 
            rec.total_remaining_amount = rec.amount_residual
            rec.paid = rec.amount_residual <= 0.0001


    
    @api.depends('amount', 'invoice_id.amount_residual')
    def _compute_total_paid_amount(self):
        for rec in self:
            residual = rec.invoice_id.amount_residual if rec.invoice_id else rec.amount
            rec.total_paid_amount = rec.amount - residual

    @api.depends('invoice_id', 'invoice_id.payment_state', 'invoice_id.line_ids', 'invoice_id.line_ids.move_id', 'invoice_id.line_ids.move_id.payment_ids')
    def _compute_paid_amount_simple(self):
        Payment = self.env['account.payment']
        for rec in self:
            payments = Payment.search([
                ('loan_line_rs_own_id', '=', rec.id),
                ('state', '=', 'posted')
            ])
            rec.total_paid_amount = sum(payments.mapped('amount'))
    
    @api.onchange('discount_percent', 'amount')
    def _onchange_discount(self):
        for rec in self:
            if rec.discount_percent:
                if not rec.original_amount:
                    rec.original_amount = rec.amount
                rec.amount = rec.original_amount * (1.0 - (rec.discount_percent / 100.0))
            else:
                if rec.original_amount:
                    rec.amount = rec.original_amount

    def send_multiple_installments(self):
        ir_model_data = self.env['ir.model.data']
        installment_template_id = ir_model_data.get_object_reference('kx_realestate', 'email_template_installment_notification')[1]
        template_res = self.env['mail.template']
        template = template_res.browse(installment_template_id)
        template.send_mail(self.id, force_send=True)

    def _get_required_stage_record(self):
        self.ensure_one()
        if self.trigger_level == 'building':
            return self.progress_building_stage_id
        if self.trigger_level == 'floor':
            return self.progress_floor_stage_id
        if self.trigger_level == 'unit':
            return self.progress_unit_stage_id
        return self.env[self._get_stage_model_name()]

    def _get_trigger_object(self):
        self.ensure_one()
        if self.trigger_level == 'building':
            return (self.loan_id.building_id or self.loan_id.building_unit_id.building_id)
        if self.trigger_level == 'unit':
            return self.loan_id.building_unit_id
        return self.loan_id.floor_id

    def _get_stage_model_name(self):
        self.ensure_one()
        return {
            'building': 're.building.stage',
            'floor': 're.floor.stage',
            'unit': 're.unit.stage',
        }.get(self.trigger_level, 're.floor.stage')

    def _stage_rank(self, stage_code):
        self.ensure_one()
        model_name = self._get_stage_model_name()
        rank_map = self.env[model_name].get_stage_rank_map(
            building_type_id=self.trigger_building_type_id.id
        )
        return rank_map.get(stage_code or 'planned', 0)

    def _is_progress_ready(self):
        self.ensure_one()
        trigger_obj = self._get_trigger_object()
        if not trigger_obj:
            return False

        stage_ready = True
        percent_ready = True
        required_stage = self._get_required_stage_record()
        if required_stage:
            current_code = trigger_obj.stage_id.code if trigger_obj.stage_id else False
            required_code = required_stage.code
            stage_ready = self._stage_rank(current_code) >= self._stage_rank(required_code)
        if self.progress_percent:
            percent_ready = trigger_obj.progress_percent >= self.progress_percent
        return stage_ready and percent_ready

    @api.onchange('trigger_level')
    def _onchange_trigger_level_clear_stages(self):
        self.progress_building_stage_id = False
        self.progress_floor_stage_id = False
        self.progress_unit_stage_id = False

    def _stage_matches_trigger(self, trigger_obj):
        self.ensure_one()
        required_stage = self._get_required_stage_record()
        if not required_stage:
            return False
        if not trigger_obj:
            return False
        if not trigger_obj.stage_id:
            return False
        return (
            trigger_obj.stage_id.code
            and required_stage.code
            and trigger_obj.stage_id.code == required_stage.code
        )
    
    def _floor_stage_matches_selected_floor(self):
        self.ensure_one()
        if not self.selected_floor_id:
            return False
        if not self.progress_floor_stage_id:
            return False
        if not self.selected_floor_id.stage_id:
            return False
        return (self.selected_floor_id.stage_id.code == self.progress_floor_stage_id.code)

    @api.model
    def process_selected_floor_stage_notifications(self, floors):
        today = fields.Date.today()
        installments = self.search([
            ('selected_floor_id', 'in', floors.ids),
            ('progress_floor_stage_id', '!=', False),
        ])
        _logger.info("SELECTED FLOOR STAGE CHANGED")
        _logger.info("Floors: %s", floors.ids)
        _logger.info("Installments Found: %s", installments.ids)

        for line in installments:
            floor = line.selected_floor_id
            if not floor.stage_id:
                continue
            if floor.stage_id.id != line.progress_floor_stage_id.id:
                continue
            if line.last_stage_notification_date == today:
                continue
            message = _('Floor "%s" reached stage "%s" for contract %s.') % (
                floor.name,
                floor.stage_id.name,
                line.loan_id.name,
            )
            _logger.info("SMS TRIGGERED FOR INSTALLMENT: %s", line.id)
            line._send_installment_notifications(message)
            line.last_stage_notification_date = today

    def _notify_on_stage_match(self):
        for line in self:
            line.action_refresh_eligibility()
            if line._stage_matches_trigger(line._get_trigger_object()):
                line.action_send_installment_sms()
                line.action_send_installment_notification()

    def action_refresh_eligibility(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.paid:
                rec.eligibility_state = 'paid'
            elif rec.invoice_id:
                rec.eligibility_state = 'invoiced'
            elif not rec.invoice_id:
                rec.eligibility_state = 'eligible'
            else:
                rec.eligibility_state = 'pending'
            rec.last_eligibility_check = now

    def action_mark_eligible(self):
        for rec in self:
            rec.write({'eligibility_state': 'eligible'})

    def _normalize_phone_number(self, phone):
        phone = (phone or '').strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "251" + phone[1:]
        elif phone.startswith("+251"):
            phone = "251" + phone[4:]
        elif not phone.startswith("251"):
            phone = "251" + phone[-9:]
        return phone

    def send_sms(self, phone, message):
        if not phone:
            return False
        try:
            # geezsms_token = self.env['ir.config_parameter'].sudo().get_param('geezsms.token')
            # geezsms_shortcode_id = self.env['ir.config_parameter'].sudo().get_param('geezsms.shortcode_id')
            # api_url = self.env['ir.config_parameter'].sudo().get_param('geezsms.sms_endpoint')

            geezsms_token = self.env['ir.config_parameter'].sudo().get_param('geezsms.token', 'BnkRsVSiNEyPNT6PT1P8I8BXKxlTuUHM')
            geezsms_shortcode_id = self.env['ir.config_parameter'].sudo().get_param('geezsms.shortcode_id', '1016')
            api_url = self.env['ir.config_parameter'].sudo().get_param('geezsms.sms_endpoint', 'https://api.geezsms.com/api/v1/sms/send')


            if not geezsms_token:
                raise UserError(_("GeezSMS token is not configured."))
            normalized_phone = self._normalize_phone_number(phone)
            payload = {
                'token': geezsms_token,
                'phone': normalized_phone,
                'msg': message,
            }
            if geezsms_shortcode_id:
                payload['shortcode_id'] = geezsms_shortcode_id
            response = requests.post(
                api_url,
                json=payload,
                timeout=10
            )
            # response = requests.post(
            #     api_url,
            #     json=payload,
            #     timeout=10
            # )
            # if response.status_code != 200:
            #     raise UserError(_("SMS sending failed.\nStatus: %s\nResponse: %s") % (response.status_code,response.text))
            # return True
            return response.status_code == 200
        except Exception as e:
            raise UserError(_("SMS Error: %s", str(e)))
            # return False
    def _can_send_notification(self, last_date):
        self.ensure_one()
        today = fields.Date.today()
        if not last_date:
            return True
        days = (today - last_date).days
        if self.notification_frequency == 'weekly':
            return days >= 7
        if self.notification_frequency == 'monthly':
            return days >= 30
        return False

    def _send_installment_notifications(self, message):
        self.ensure_one()
        phones = set()
        if self.loan_id.user_id.partner_id.phone:
            phones.add(self.loan_id.user_id.partner_id.phone)
        if self.loan_id.partner_id.phone:
            phones.add(self.loan_id.partner_id.phone)
        if self.loan_id.phone:
            phones.add(self.loan_id.phone)
        if self.loan_id.signed_by_other_phone:
            phones.add(self.loan_id.signed_by_other_phone)
        # if self.loan_id.seller_company_phone:
        #     phones.add(self.loan_id.seller_company_phone)
        _logger.info("SMS Phones Found: %s", list(phones))
        for phone in phones:
            _logger.info("Sending SMS to: %s", phone)
            result = self.send_sms(phone, message)
            _logger.info("SMS Result for %s : %s", phone, result)
        if self.loan_id.user_id:
            self.loan_id.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.loan_id.user_id.id,
                summary=_('Installment Notification'),
                note=message,)
            
    @api.model
    def process_stage_change_notifications(self, trigger_level, records):
        today = fields.Date.today()
        domain = [
            ('trigger_level', '=', trigger_level),
            ('paid', '=', False),
            ('loan_id.state', '=', 'confirmed'),
        ]
        if trigger_level == 'building':
            domain.append((
                'loan_id.building_unit_id.building_id',
                'in',records.ids))
        elif trigger_level == 'floor':
            domain.append((
                'loan_id.building_unit_id.floor_id',
                'in',records.ids))
        elif trigger_level == 'unit':
            domain.append((
                'loan_id.building_unit_id',
                'in',records.ids))
        installments = self.search(domain)
        _logger.info("STAGE CHANGED")
        _logger.info("Trigger Level: %s", trigger_level)
        _logger.info("Records: %s", records.ids)
        _logger.info("Installments Found: %s", installments.ids)

        for line in installments:
            trigger_obj = line._get_trigger_object()
            if not trigger_obj:
                continue
            _logger.info(
                "Checking installment %s | Required=%s | Current=%s",
                line.id,
                line._get_required_stage_record().code if line._get_required_stage_record() else '',
                trigger_obj.stage_id.code if trigger_obj.stage_id else '',
            )
            if line._stage_matches_trigger(trigger_obj):
                if line.last_stage_notification_date == today:
                    continue
                stage_name = trigger_obj.stage_id.name if trigger_obj.stage_id else ''
                message = _(
                    'Construction progress reached stage "%s" '
                    'for contract %s.'
                ) % (
                    stage_name,line.loan_id.name,)
                line._send_installment_notifications(message)
                line.last_stage_notification_date = today
                line.action_refresh_eligibility()
            
    def action_send_installment_notification(self):
        for rec in self:
            message = _('Installment "%s" for contract %s requires attention.') % (rec.number,rec.loan_id.name,)
            if rec.loan_id.user_id:
                rec.loan_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=rec.loan_id.user_id.id,
                    summary=_('Installment Notification'),
                    note=message,)
        return True

    def action_send_installment_sms(self):
        for rec in self:
            message = _('Installment "%s" for contract %s requires attention.') % (rec.number,rec.loan_id.name,)
            rec._send_installment_notifications(message)
        return True

    def process_installment_reminders(self):
        today = fields.Date.today()
        lines = self.search([('loan_id.state', '=', 'confirmed')])
        for rec in lines:
            rec.action_refresh_eligibility()
            due_date = rec.trigger_date or rec.date
            reminder_state = 'none'
            if rec.paid:
                reminder_state = 'none'
            elif due_date:
                if due_date < today:
                    reminder_state = 'overdue'
                elif due_date == today:
                    reminder_state = 'due'
                elif (due_date - today).days <= 7:
                    reminder_state = 'upcoming'
            if rec.reminder_state != reminder_state:
                rec.reminder_state = reminder_state
            should_notify = reminder_state in ('due', 'overdue')
            if should_notify and rec.reminder_last_date != today:
                if rec.contract_partner_id.email:
                    rec.send_multiple_installments()
                if rec.loan_id.user_id:
                    rec.loan_id.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=rec.loan_id.user_id.id,
                        summary=_('Installment Follow-up'),
                        note=_('%s for %s is %s.') % (
                            rec.name,
                            rec.contract_partner_id.name,
                            reminder_state,
                        ),
                    )
                rec.reminder_last_date = today

    @api.model
    def cron_send_due_and_stage_notifications(self):
        today = fields.Date.today()
        lines = self.search([('loan_id.state', '=', 'confirmed'),('paid', '=', False),])
        for rec in lines:
            due_date = rec.trigger_date or rec.date
            due_trigger = due_date == today
            if due_trigger and rec._can_send_notification(rec.reminder_last_date):
                message = _('Installment "%s" for contract %s is due today.') % (rec.name,rec.loan_id.name,)
                rec._send_installment_notifications(message)
                rec.reminder_last_date = today

            trigger_obj = rec._get_trigger_object()
            if not trigger_obj:
                continue

            level_name = {
                'building': _('building %s') % trigger_obj.name,
                'floor': _('floor %s') % trigger_obj.name,
                'unit': _('unit %s') % trigger_obj.name,
            }.get(rec.trigger_level, trigger_obj.name)

            if rec._stage_matches_trigger(trigger_obj) and rec._can_send_notification(rec.last_stage_notification_date):
                stage_name = trigger_obj.stage_id.name if trigger_obj.stage_id else ""
                message = _('Construction progress reached stage "%s" for contract %s on %s.') % (
                    stage_name, rec.loan_id.name, level_name,
                )
                rec._send_installment_notifications(message)
                rec.last_stage_notification_date = today
    
    def make_invoice(self, post=False):
        for rec in self:
            rec.action_refresh_eligibility()
            if rec.eligibility_state not in ('eligible', 'invoiced'):
                raise UserError(_('This installment is not eligible for invoicing yet.'))
            if rec.invoice_id:
                continue
            account_move_obj = self.env['account.move']
            journal_pool = self.env['account.journal']
            journal = journal_pool.search([('type', '=', 'sale')], limit=1)
            vals = {
                'partner_id': rec.contract_partner_id.id,
                'move_type': 'out_invoice',
                'loan_line_rs_own_id': rec.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': rec.date or rec.trigger_date or fields.Date.today(),
                'invoice_line_ids': [(0, None, {
                    'quantity': 1,
                    'price_unit': rec.amount,
                    'name': 'Loan Installment',
                })]
            }
            if rec.loan_id.building_unit_id:
                product = rec.loan_id.building_unit_id
                vals['invoice_line_ids'] = [(0, None, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': rec.amount,
                    'name': product.name,
                })]
            invoice = account_move_obj.create(vals)
            if post:
                invoice.action_post()
            rec.invoice_id = invoice.id
            rec.eligibility_state = 'invoiced'

    def register_customer_payment_via_invoice(self, amount, payment_date, journal, communication=''):
        self.ensure_one()
        if amount <= 0:
            raise UserError(_('Payment amount must be positive.'))
        if amount > self.total_remaining_amount:
            raise UserError(_('You cannot pay more than the required amount!'))
        if not self.invoice_id:
            self.make_invoice(post=True)
        elif self.invoice_id.state == 'draft':
            self.invoice_id.action_post()
        invoice = self.invoice_id
        if invoice.payment_state == 'paid':
            return self.env['account.payment']

        register_ctx = {
            'active_model': 'account.move',
            'active_ids': [invoice.id],
        }
        wizard = self.env['account.payment.register'].with_context(register_ctx).create({
            'amount': amount,
            'payment_date': payment_date or fields.Date.today(),
            'journal_id': journal.id,
            'communication': communication or (self.loan_id.name + ' - ' + self.name),
        })
        wizard.action_create_payments()
        payments = self.env['account.payment'].search([
            ('partner_id', '=', self.contract_partner_id.id),
            ('amount', '=', amount),
            ('date', '=', payment_date or fields.Date.today()),
            ('state', 'in', ('draft', 'posted')),
        ], order='id desc', limit=5)
        if payments:
            payments.filtered(lambda p: not p.loan_line_rs_own_id).write({'loan_line_rs_own_id': self.id})
        # self.total_paid_amount += amount
        self.action_refresh_eligibility()
        posted_payment = payments.filtered(lambda p: p.state == 'posted')[:1]
        self.loan_id.get_commission_paid(amount, payment_date, posted_payment.id if posted_payment else False)
        return payments

    def view_invoice(self):
        move = self.env['account.move'].sudo().search([('loan_line_rs_own_id','=',self.id)])
        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'res_id':move.id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
