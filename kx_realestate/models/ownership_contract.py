import calendar
from datetime import date
import math
from odoo import api, fields, models, _
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError

class OwnershipContract(models.Model):
    _name = "ownership.contract"
    _description = "Ownership Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_income_account(self):
        params = self.env['ir.config_parameter'].sudo()
        return (
            params.get_param('kx_real_estate.account_id')
            or params.get_param('kx_realestate.account_id')
            or params.get_param('kx_realestate.income_account')
        )

    amount_total = fields.Float(string='Total', compute='_check_amounts', store=True)
    agreement_type = fields.Selection(
        [
            ('date_based', 'Date Based'),
            ('progress_based', 'Progress Based'),
            ('mixed', 'Mixed'),
            ('manual', 'Manual'),
        ],
        default='date_based',
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    address = fields.Char(string='Address')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    account_id = fields.Many2one('account.account', string='Income Account', default=_default_income_account,)
    building_attachment_line_ids = fields.One2many("own.attachment.line", "ownership_contract_id", string="Documents")
    balance = fields.Float(string='Balance', compute='_check_amounts', store=True)
    site_id = fields.Many2one('re.site', string='Site', copy=False)
    block_id = fields.Many2one('re.block', string='Block', copy=False)
    building_id = fields.Many2one('building.building', string='Building', copy=False)
    building_code = fields.Char(string='Code')
    building_unit_id = fields.Many2one('product.template', string='Unit', copy=False)
    building_unit_ids = fields.Many2many('product.template', string='Units')
    @api.onchange('building_unit_id')
    def onchange_units(self):
        if self.building_unit_id:
            unit = self.building_unit_id
            self.unit_code = unit.code
            self.floor = unit.floor
            self.selling_price = unit.selling_price
            self.building_type_id = unit.building_type_id
            self.address = unit.address
            self.building_status_id = unit.building_status_id
            # self.building_unit_area = unit.building_unit_area
            self.building_id = unit.building_id.id
            self.primary_address = unit.building_id.address or unit.address
        else:
            self.unit_code = False
            self.floor = False
            self.selling_price = False
            self.building_type_id = False
            self.address = False
            self.building_status_id = False
            # self.building_unit_area = False
            self.building_id = False
            self.primary_address = False
    building_status_id = fields.Many2one('building.status', string='Building Unit Status')
    building_type_id = fields.Many2one('building.type', string='Building Unit Type')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    commission_paid_amount = fields.Float(string='Released Commission', compute='_compute_commission_totals')
    commission_percent = fields.Float(string='Commission %', default=lambda self: self.env.user.realestate_commission_percent)
    commission_release_policy = fields.Selection(
        [('on_payment', 'On Payment'), ('on_confirm', 'On Confirmation')],
        default=lambda self: self.env.user.realestate_commission_release_policy or 'on_payment',
        string='Commission Release Policy',
    )
    date = fields.Datetime(string='Date',required=True, default=fields.Datetime.now)
    invoice_count = fields.Integer(string='Customer Invoices', compute='_compute_invoice_count')
    first_payment_date = fields.Date(string='First Payment Date')
    floor = fields.Char(string='Floor')
    floor_id = fields.Many2one('re.floor', string='Floor', related='building_unit_id.floor_id', store=True, readonly=True)
    garage_date = fields.Date(string='Garage Date')
    garage_included = fields.Float(string='Garage', digits='Product Price')
    installment_template_id = fields.Many2one('installment.template', string='Payment Template')
    loan_line_rs_own_ids = fields.One2many('loan.line.rs.own', 'loan_id',string="Installments", store=True)

    loan_line_count = fields.Integer(
        string="Installments Count",
        compute="_compute_loan_line_count",
        store=True
    )
    installment_names = fields.Char(
        string="Installment Names",
        compute="_compute_installment_names",
        store=True
    )
    payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ], compute='_compute_payment_status', store=True)

    warning_letter_ids = fields.One2many('warning.letter', 'ownership_contract_id', string='Warning Letter')


    @api.depends('loan_line_rs_own_ids.payment_state')
    def _compute_payment_status(self):
        for rec in self:
            states = rec.loan_line_rs_own_ids.mapped('payment_state')
            if not states:
                rec.payment_status = 'not_paid'
            elif all(s == 'paid' for s in states):
                rec.payment_status = 'paid'
            elif any(s in ('partial', 'in_payment') for s in states):
                rec.payment_status = 'partial'
            else:
                rec.payment_status = 'not_paid'

    paid_count = fields.Integer(compute='_compute_line_status_counts', store=True)
    unpaid_count = fields.Integer(compute='_compute_line_status_counts', store=True)
    @api.depends('loan_line_rs_own_ids.paid')
    def _compute_line_status_counts(self):
        for rec in self:
            paid_lines = rec.loan_line_rs_own_ids.filtered(lambda l: l.paid)
            rec.paid_count = len(paid_lines)
            rec.unpaid_count = len(rec.loan_line_rs_own_ids) - len(paid_lines)

    @api.depends('loan_line_rs_own_ids.name')
    def _compute_installment_names(self):
        for rec in self:
            names = rec.loan_line_rs_own_ids.mapped('name')
            names = [str(n) for n in names if n]
            rec.installment_names = ', '.join(names)

    @api.depends('loan_line_rs_own_ids')
    def _compute_loan_line_count(self):
        for rec in self:
            rec.loan_line_count = len(rec.loan_line_rs_own_ids)
    total_paid_amount = fields.Float(
        string='Total Collected Amount',
        compute='_compute_amounts',
        store=True
    )

    total_remaining_amount = fields.Float(
        string='Total Remaining Amount',
        compute='_compute_amounts',
        store=True
    )

    all_paid = fields.Boolean(
        string='All Paid',
        compute='_compute_amounts',
        store=True
    )
    @api.depends('loan_line_rs_own_ids.total_paid_amount','loan_line_rs_own_ids.total_remaining_amount','loan_line_rs_own_ids.paid')
    def _compute_amounts(self):
        for rec in self:
            lines = rec.loan_line_rs_own_ids

            rec.total_paid_amount = sum(lines.mapped('total_paid_amount'))
            rec.total_remaining_amount = sum(lines.mapped('total_remaining_amount'))
            rec.all_paid = all(lines.mapped('paid')) if lines else False

    maintenance_date = fields.Date(string='Maintenance Date')
    name = fields.Char(string='Name', readonly=True)
    no_of_floors = fields.Integer(string='Floors')
    origin = fields.Char(string='Source Document')
    other_expenses_date = fields.Date(string='Other Expenses Date')
    other = fields.Float(string='Other Expenses', digits='Product Price')
    paid = fields.Float(string='Paid', compute='_check_amounts', store=True)
    payment_initiator = fields.Char(string='Payment Initiator')
    partner_id = fields.Many2one('res.partner', string='Customer', required=False)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    seller_company_name = fields.Char(related='company_id.name', string='Seller / Builder', readonly=True)
    seller_company_street = fields.Char(related='company_id.partner_id.street', string='Address', readonly=True)
    seller_company_street2 = fields.Char(related='company_id.partner_id.street2', string='Address 2', readonly=True)
    seller_company_city = fields.Char(related='company_id.partner_id.city', string='City', readonly=True)
    seller_company_phone = fields.Char(related='company_id.partner_id.phone', string='Phone', readonly=True)
    seller_company_vat = fields.Char(related='company_id.partner_id.vat', string='VAT / Tax No.', readonly=True)
    preferred_communication_channel = fields.Selection(
        [('email', 'Email'), ('phone', 'Phone'), ('whatsapp', 'WhatsApp'), ('letter', 'Letter')],
        default='email',
        string='Preferred Communication Channel',
    )
    preferred_communication_method_ids = fields.Many2many(
        're.communication.method',
        'own_contract_preferred_comm_rel',
        'contract_id',
        'method_id',
        string='Preferred Communication Methods',
    )
    primary_address = fields.Text(string='Primary Address')
    secondary_address = fields.Text(string='Secondary Address')
    legal_communication_method = fields.Selection(
        [('email', 'Email'), ('sms', 'SMS'), ('letter', 'Letter'), ('courier', 'Courier')],
        default='email',
        string='Legal Communication Method',
    )
    legal_communication_method_ids = fields.Many2many(
        're.communication.method',
        'own_contract_legal_comm_rel',
        'contract_id',
        'method_id',
        string='Legal Communication Methods',
    )
    contract_sign_date = fields.Date(string='Contract Sign Date')
    signed_by = fields.Selection(
        [('customer', 'Customer'), ('other', 'Other')],
        default='customer',
        string='Signed By',
    )
    signed_by_other = fields.Char(string='Signed By (Other)')
    signed_by_other_phone = fields.Char(string='Signed By (Other) Phone')
    signed_by_other_document = fields.Binary(string='Signed By (Other) Document')
    signed_by_other_document_name = fields.Char(string='Signed By (Other) Document Name')
    reservation_id = fields.Many2one('unit.reservation', string='Reservation')
    selling_price = fields.Float(string='Price', digits='Product Price', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('closed', 'Closed')], default='draft', string="State")
    unit_code = fields.Char(string='Code')
    building_address = fields.Char(related='building_id.address', string='Building Address', readonly=True)
    building_state_id = fields.Many2one(related='building_id.state_id', string='Building State', readonly=True)
    building_city = fields.Char(related='building_id.city', string='Building City', readonly=True)
    building_woreda = fields.Char(related='building_id.woreda', string='Building Woreda', readonly=True)
    building_kebele = fields.Char(related='building_id.kebele', string='Building Kebele', readonly=True)
    building_title_deed_no = fields.Char(related='building_id.title_deed_no', string='Title Deed No.', readonly=True)
    building_title_deed_date = fields.Date(related='building_id.title_deed_date', string='Title Deed Date', readonly=True)
    buyer_responsibility_ids = fields.One2many(
        'ownership.buyer.responsibility',
        'ownership_contract_id',
        string='Buyer Responsibility',
    )
    seller_responsibility_ids = fields.One2many(
        'ownership.seller.responsibility',
        'ownership_contract_id',
        string='Seller / Builder Responsibility',
    )
    handover_checklist_ids = fields.One2many(
        'ownership.handover.checklist',
        'ownership_contract_id',
        string='Handover Checklist',
    )
    is_fully_paid = fields.Boolean(
        string="Fully Paid",
        compute="_compute_is_fully_paid",
        store=True
    )
    term_penalty_rule_ids = fields.One2many(
        'ownership.term.penalty.rule',
        'ownership_contract_id',
        string='Terms & Penalty Rules',
    )
    trigger_policy = fields.Selection(
        [('auto_invoice', 'Create Draft Invoice'), ('notify_only', 'Notify Finance'), ('manual', 'Manual Release')],
        default='auto_invoice',
        required=True,
        tracking=True,
    )
    all_invoices_paid = fields.Boolean(compute='_compute_all_invoices_paid', string='All Invoices Paid')

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    @api.depends('loan_line_rs_own_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 0
        if not self.ids:
            return
        groups = self.env['account.move'].read_group(
            [('ownership_id', 'in', self.ids)],
            ['__count'],
            ['ownership_id'],
            lazy=False,
        )
        counts = {g['ownership_id'][0]: g['__count'] for g in groups if g.get('ownership_id')}
        for rec in self:
            rec.invoice_count = counts.get(rec.id, 0)


    @api.depends('loan_line_rs_own_ids.payment_state')
    def _compute_is_fully_paid(self):
        for rec in self:
            lines = rec.loan_line_rs_own_ids
            rec.is_fully_paid = bool(lines) and all(
                line.payment_state == 'paid' for line in lines
            )

    @api.depends('loan_line_rs_own_ids.invoice_state')
    def _compute_all_invoices_paid(self):
        for record in self:
            all_paid = all(line.invoice_state in ['posted', 'paid'] for line in record.loan_line_rs_own_ids)
            record.all_invoices_paid = all_paid
    
    @api.model
    def user_has_access(self, group_xml_id):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if group:
            return group in self.env.user.groups_id
        return False

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'confirmed':
            if not self.user_has_access('contract_edit_group_xml_id') and not self.user_has_access('contract_supervisor_group_xml_id'):
                raise UserError("You do not have permission to edit this contract.")
        elif self.state == 'closed':
            if not self.user_has_access('contract_supervisor_group_xml_id'):
                raise UserError("You do not have permission to edit this contract.")
    
    @api.depends('loan_line_rs_own_ids.amount','loan_line_rs_own_ids.amount_residual')
    def _check_amounts(self):
        total_paid = 0
        total_nonpaid = 0
        amount_total = 0
        for rec in self:
            total_paid = 0
            total_nonpaid = 0
            amount_total = 0
            total_discount = 0
            for line in rec.loan_line_rs_own_ids:
                amount_total += line.amount
                total_nonpaid += line.total_remaining_amount
                total_paid += line.total_paid_amount or (line.amount - line.total_remaining_amount)
                if line.original_amount:
                    total_discount += (line.original_amount - line.amount)
            rec.paid = total_paid
            rec.balance = total_nonpaid
            rec.amount_total = amount_total
            rec.discount_total = total_discount

    discount_total = fields.Float(string='Total Discount', compute='_check_amounts', store=True)

    @api.constrains('loan_line_rs_own_ids', 'selling_price','club', 'maintenance', 'garage_included','elevator', 'other')
    def _check_totals_warning(self):
        for rec in self:
            if not rec.loan_line_rs_own_ids:
                continue
            expected_total = rec.selling_price or 0.0
            for f in ['club', 'maintenance', 'garage_included', 'elevator', 'other']:
                expected_total += getattr(rec, f, 0.0) or 0.0
            calculated_original_total = sum( line.original_amount or line.amount for line in rec.loan_line_rs_own_ids)
            if abs(calculated_original_total - expected_total) > 0.01:
                raise ValidationError(_(
                    "Total mismatch.\n\n"
                    "Installments total: %.2f\n"
                    "Expected total: %.2f\n\n"
                    "Discount differences are ignored."
                ) % (calculated_original_total, expected_total))

    @api.depends('loan_line_rs_own_ids')
    def _voucher_count(self):
        for rec in self:
            rec.voucher_count = 0
        if not self.ids:
            return
        payments = self.env['account.payment'].search([('loan_line_rs_own_id.loan_id', 'in', self.ids)])
        counts = {}
        for pay in payments:
            line = pay.loan_line_rs_own_id
            if line and line.loan_id:
                cid = line.loan_id.id
                counts[cid] = counts.get(cid, 0) + 1
        for rec in self:
            rec.voucher_count = counts.get(rec.id, 0)

    @api.depends('loan_line_rs_own_ids.invoice_id.amount_untaxed', 'loan_line_rs_own_ids.invoice_id.amount_tax')
    def _compute_sample_vat_percent(self):
        for rec in self:
            untaxed = 0.0
            tax = 0.0
            for invoice in rec.loan_line_rs_own_ids.mapped('invoice_id'):
                if not invoice:
                    continue
                untaxed += invoice.amount_untaxed
                tax += invoice.amount_tax
            rec.sample_effective_vat_percent = (tax * 100.0 / untaxed) if untaxed else 0.0

    
    def unlink(self):
        if self.state != 'draft':
            raise UserError(_('You can not delete a contract not in draft state'))
        super(OwnershipContract, self).unlink()

    def view_vouchers(self):
        self.ensure_one()
        voucher_ids = self.env['account.payment'].search([
            ('loan_line_rs_own_id.loan_id', '=', self.id)
        ]).ids
        return {
            'name': _('Receipts'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', voucher_ids)],
            'target': 'current',
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Customer Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('ownership_id', '=', self.id), ('move_type', '=', 'out_invoice')],
            'target': 'current',
        }

    def action_view_commission_lines(self):
        self.ensure_one()
        return {
            'name': _('Commissions'),
            'type': 'ir.actions.act_window',
            'res_model': 'salesperson.commission.line',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
            'target': 'current',
        }

    def action_open_customer_payment_wizard(self):
        self.ensure_one()
        return {
            'name': _('Customer Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'customer.payment.check',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    @api.model
    def create(self, vals):
        if vals.get('building_unit_id') and not vals.get('building_id'):
            unit = self.env['product.template'].browse(vals['building_unit_id'])
            vals['building_id'] = unit.building_id.id
        vals['name'] = self.env['ir.sequence'].next_by_code('ownership.contract')
        new_id = super(OwnershipContract, self).create(vals)

        return new_id

    def unit_status(self):
        return self.building_unit_id.state

    def write(self, vals):
        if vals.get('building_unit_id') and not vals.get('building_id'):
            unit = self.env['product.template'].browse(vals['building_unit_id'])
            vals['building_id'] = unit.building_id.id
        res = super().write(vals)
        self._check_penalty_rules()
        return res
        
    def _check_penalty_rules(self):
        rules = self.env['ownership.term.penalty.rule'].search([('ownership_contract_id', 'in', self.ids)])
        for rule in rules:
            rule._matches_contract_domain(rule.ownership_contract_id)

    def action_confirm(self):
        for rec in self:
            unit = rec.building_unit_id
            unit.write({'state' : 'sold'})
            if not rec.reservation_id or rec.reservation_id.contract_count_own == 0:
                rec.state = 'confirmed'
            elif rec.reservation_id.contract_count_own >= 1:
                if rec.reservation_id.contract_count_own > 1:
                    rec.state = 'resell'
                else:
                    if rec.state == 'draft':
                        rec.state = 'confirmed'
            rec.loan_line_rs_own_ids.action_refresh_eligibility()

            # if hasattr(rec, 'commission_release_policy') and rec.commission_release_policy == 'on_confirm':
            #     if rec.commission_percent and hasattr(rec, 'commission_line_ids') and not rec.commission_line_ids:
            #         self.env['salesperson.commission.line'].create({
            #             'amount': rec.commission_expected_amount if hasattr(rec, 'commission_expected_amount') else 0.0,
            #             'amount_base': rec.selling_price,
            #             'commission_percent': rec.commission_percent,
            #             'contract_id': rec.id,
            #             'release_date': fields.Date.today(),
            #             'state': 'earned',
            #             'user_id': rec.user_id.id,
            #             'company_id': rec.company_id.id,
            #             'note': _('Released on contract confirmation'),
            #         })
            if hasattr(rec, 'action_evaluate_sample_penalty_rules'):
                rec.action_evaluate_sample_penalty_rules()
            if hasattr(rec, 'action_evaluate_custom_penalty_rules'):
                rec.action_evaluate_custom_penalty_rules()

    def action_create_invoice(self):
        self.ensure_one()
        account = self.account_id or self.building_unit_id.property_account_income_id
        if not account:
            account = self.building_id.account_id
        
        if not account:
            raise UserError(_('Please set an Income Account on the contract or the Unit/Building before creating an invoice.'))
        
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError(_('Please configure a Sales Journal.'))

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'ref': self.name,
            'ownership_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': _('Contract: %s') % self.name,
                'product_id': self.building_unit_id.id,
                'quantity': 1,
                'price_unit': self.selling_price,
                'account_id': account.id,
                'analytic_account_id': self.analytic_account_id.id,
            })],
        }
        invoice = self.env['account.move'].create(invoice_vals)
        return {
            'name': _('Customer Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    # @api.model
    def action_set_closed(self):
        for record in self:
            if self.env.user.has_group('kx_realestate.group_contract_supervisor'):
                record.state = 'closed'
            else:
                raise UserError(_('You do not have permission to set the contract to closed.'))

    # @api.model
    def action_reset_to_draft(self):
        for record in self:
            if self.env.user.has_group('kx_realestate.group_contract_supervisor'):
                record.state = 'draft'
            else:
                raise UserError(_('You do not have permission to reset the contract to draft.'))

    def action_cancel(self):
        for rec in self:
            unit = rec.building_unit_id
            unit.write({'state' : 'free'})
            rec.write({'state' : 'cancel'})
            # rec.commission_line_ids.filtered(lambda line: line.state != 'paid').write({'state': 'cancelled'})
            for line in rec.loan_line_rs_own_ids:
                if line.invoice_id:
                    line.invoice_id.button_draft()
                    line.invoice_id.button_cancel()
            rec.action_evaluate_sample_penalty_rules()
            rec.action_evaluate_custom_penalty_rules()

    @api.onchange('building_id')
    def onchange_building(self):
        if self.building_id:
            units = self.env['product.template'].search([('is_property', '=', True),('building_id', '=', self.building_id.id),('state','=','free')])
            unit_ids = []
            for u in units : unit_ids.append(u.id)
            building_obj = self.env['building.building'].browse(self.building_id.id)
            code = building_obj.code
            no_of_floors = building_obj.no_of_floors
            analytic_account_id = building_obj.analytic_account_id.id
            if building_obj:
                self.building_code = code
                self.no_of_floors = no_of_floors
                return {'domain': {'building_unit_id': [('id', 'in', unit_ids)]}}

    def add_months(self,sourcedate,months):
        month = sourcedate.month - 1 + months
        year = int(sourcedate.year + month / 12 )
        month = month % 12 + 1
        day = min(sourcedate.day,calendar.monthrange(year,month)[1])
        return date(year,month,day)

    @api.onchange('building_unit_id')
    def onchange_unit(self):
        unit = self.building_unit_id
        if not unit:
            return
        self.unit_code = unit.code
        self.floor = unit.floor
        self.selling_price = unit.selling_price
        self.building_type_id = unit.building_type_id
        self.address = unit.address
        self.building_status_id = unit.building_status_id
        self.building_id = unit.building_id.id
        self.primary_address = unit.building_id.address or unit.address

    @api.onchange('reservation_id')
    def onchange_reservation(self):
        self.building_id = self.reservation_id.building_id.id
        self.building_code = self.reservation_id.building_code
        self.partner_id = self.reservation_id.partner_id.id
        self.building_unit_id = self.reservation_id.building_unit_id.id
        self.unit_code = self.reservation_id.unit_code
        self.address = self.reservation_id.address
        self.floor = self.reservation_id.floor
        self.selling_price = self.reservation_id.selling_price
        self.first_payment_date = self.reservation_id.first_payment_date
        self.installment_template_id = self.reservation_id.installment_template_id.id
        self.building_type_id = self.reservation_id.building_type_id
        self.building_status_id = self.reservation_id.building_status_id
        self.primary_address = self.reservation_id.address
        if self.installment_template_id:
            loan_lines=self._prepare_lines(self.first_payment_date)
            self.loan_line_rs_own_ids = loan_lines

    @api.onchange('partner_id')
    def _onchange_partner_details(self):
        if self.partner_id:
            self.phone = self.partner_id.phone or self.partner_id.mobile
            self.email = self.partner_id.email
            self.payment_initiator = self.partner_id.name
            self.secondary_address = ', '.join(
                filter(None, [self.partner_id.street, self.partner_id.street2, self.partner_id.city])
            )

    def create_move(self,rec,debit,credit,move,account):
        move_line_obj = self.env['account.move.line']
        move_line_obj.create({
            'name': rec.name,
            'partner_id': rec.partner_id.id,
            'debit': debit,
            'credit': credit,
            'move_id': move,
        })

    def generate_entries(self):
        journal_pool = self.env['account.journal']
        journal = journal_pool.search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError(_('Please set sales accounting journal!'))
        account_move_obj = self.env['account.move']
        total = 0
        for rec in self:

            for line in rec.loan_line_rs_own_ids:
                total+=line.amount
            vals = {
                'ref': rec.name,
                'journal_id': journal.id,
                'ownership_id': rec.id,
                'line_ids': [
                    (0, 0, {
                        'name': rec.name,
                        'partner_id': rec.partner_id.id,
                        'account_id': rec.partner_id.property_account_receivable_id.id,
                        'debit': total,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': rec.name,
                        'partner_id': rec.partner_id.id,
                        'account_id': account.id,
                        'debit': 0.0,
                        'credit': total,
                    }),
                ]
            }
            account_move = account_move_obj.create(vals)

    def generate_cancel_entries(self):
        journal_pool = self.env['account.journal']
        journal = journal_pool.search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError(_('Please set sales accounting journal!'))
        total = 0
        for rec in self:

            for line in rec.loan_line_rs_own_ids:
                total += line.amount
        account_move_obj = self.env['account.move']
        move_id = account_move_obj.create({'ref': self.name,'ownership_id':rec.id,
                                           'journal_id': journal.id,
                                           'line_ids': [(0, 0, {'name': self.name,
                                                                'debit': 0.0,
                                                                'credit': total}),
                                                        (0, 0, {'name': self.name,
                                                                'debit': total,
                                                                'credit': 0.0})
                                                        ]
                                           })
        return move_id

    def _prepare_lines(self,first_date):
        self.loan_line_rs_own_ids = None
        loan_lines = []
        if self.installment_template_id:
            ind = 1
            selling_price = self.selling_price
            mon = self.installment_template_id.month
            yr = self.installment_template_id.duration_year
            repetition = self.installment_template_id.repetition_rate
            advance_percent = self.installment_template_id.advance_payment
            deducted_amount = self.installment_template_id.deducted_amount
            if not first_date:
                raise UserError(_('Please select first payment date!'))
            adv_payment=selling_price*float(advance_percent)/100
            if mon > 12:
                x = mon / 12
                mon = (x * 12) + mon % 12
            mons = mon + (yr * 12)
            trigger_type = {
                'date_based': 'date',
                'progress_based': 'progress',
                'manual': 'manual',
                'mixed': 'mixed',
            }.get(self.agreement_type, 'date')
            if adv_payment:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': adv_payment,
                    'original_amount': adv_payment,
                    'amount_type': 'fixed',
                    'amount_value': adv_payment,
                    'date': first_date,
                    'trigger_date': first_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Advance Payment'),
                }))
                ind += 1
                if deducted_amount:
                    selling_price -= adv_payment
            loan_amount = (selling_price / float(mons)) * repetition if mons else 0.0
            m = 0
            while m < mons:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': loan_amount,
                    'original_amount': loan_amount,
                    'amount_type': 'fixed',
                    'amount_value': loan_amount,
                    'date': first_date,
                    'trigger_date': first_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Loan Installment'),
                }))
                ind += 1
                first_date = self.add_months(first_date, repetition)
                m += repetition
            if self.club:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': self.club,
                    'original_amount': self.club,
                    'amount_type': 'fixed',
                    'amount_value': self.club,
                    'date': self.club_date,
                    'trigger_date': self.club_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Club Payment'),
                }))
                ind += 1
            if self.maintenance:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': self.maintenance,
                    'original_amount': self.maintenance,
                    'amount_type': 'fixed',
                    'amount_value': self.maintenance,
                    'date': self.maintenance_date,
                    'trigger_date': self.maintenance_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Maintenance Payment'),
                }))
                ind += 1
            if self.garage_included:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': self.garage_included,
                    'original_amount': self.garage_included,
                    'amount_type': 'fixed',
                    'amount_value': self.garage_included,
                    'date': self.garage_date,
                    'trigger_date': self.garage_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Garage Payment'),
                }))
                ind += 1
            if self.elevator:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': self.elevator,
                    'original_amount': self.elevator,
                    'amount_type': 'fixed',
                    'amount_value': self.elevator,
                    'date': self.elevator_date,
                    'trigger_date': self.elevator_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Elevator Payment'),
                }))
                ind += 1
            if self.other:
                loan_lines.append((0,0,{
                    'number': ind,
                    'amount': self.other,
                    'original_amount': self.other,
                    'amount_type': 'fixed',
                    'amount_value': self.other,
                    'date': self.other_expenses_date,
                    'trigger_date': self.other_expenses_date,
                    'trigger_type': trigger_type,
                    'floor_id': self.floor_id.id,
                    'name': _('Other Payment'),
                }))
                ind += 1
        return loan_lines

    def process_installment_triggers(self):
        for contract in self.search([('state', '=', 'confirmed')]):
            contract.loan_line_rs_own_ids.action_refresh_eligibility()
            contract.action_evaluate_sample_penalty_rules()
            contract.action_evaluate_custom_penalty_rules()
            for line in contract.loan_line_rs_own_ids.filtered(
                lambda installment: installment.eligibility_state == 'eligible'
                and installment.auto_invoice
                and contract.trigger_policy == 'auto_invoice'
            ):
                line.make_invoice(post=False)

    def get_commission_paid(self, amount, payment_date, payment_id=False):
        self.ensure_one()
        if not self.commission_percent or self.commission_release_policy != 'on_payment':
            return False
        return self.env['salesperson.commission.line'].create({
            'amount': amount * self.commission_percent / 100.0,
            'amount_base': amount,
            'commission_percent': self.commission_percent,
            'contract_id': self.id,
            'payment_id': payment_id,
            'release_date': payment_date or fields.Date.today(),
            'state': 'earned',
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'note': _('Released on customer payment'),
        })