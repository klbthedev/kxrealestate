from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date

class SalespersonCommissionLine(models.Model):
    _name = 'salesperson.commission.line'
    _description = 'Salesperson Commission Line'
    _order = 'release_date desc, id desc'

    sales_person = fields.Many2one('res.partner', string='Sales Person', required=True)
    user_id = fields.Many2one('res.users', string='Salesperson', required=False)
    
    amount = fields.Float(
        string='Commission Amount', 
        compute='_compute_amount', 
        store=True, 
        readonly=False, 
        required=True
    )
    amount_base = fields.Float(
        string='Base Amount',
        compute="_compute_amount_base", 
        store=True, 
        readonly=False
    )
    commission_percent = fields.Float(string='Commission %', required=True, default=0.0)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    contract_id = fields.Many2one('ownership.contract', string='Ownership Contract', required=True, ondelete='cascade')   

    commission_release_policy = fields.Selection(
        related='contract_id.commission_release_policy',
        store=True,
        readonly=True,
    )

    installment_id = fields.Many2one('loan.line.rs.own', string='Installment', ondelete='cascade')
    note = fields.Char(string='Note')
    payment_id = fields.Many2one('account.payment', string='Payment')
    release_date = fields.Date(default=fields.Date.context_today, required=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],string="Status", default='draft', tracking=True, required=True,)

    
    vendor_bill_id = fields.Many2one('account.move', string="Vendor Bill", domain=[('move_type', '=', 'in_invoice')], copy=False)
    vendor_payment_id = fields.Many2one('account.payment', string="Vendor Payment", copy=False)
    vendor_bill_state = fields.Selection(related='vendor_bill_id.state', store=True)
    vendor_payment_state = fields.Selection(related='vendor_payment_id.state', store=True)
    
    # Self-referential hierarchy
    parent_commission_id = fields.Many2one('salesperson.commission.line', string='Parent Commission', ondelete='cascade')
    installment_commission_ids = fields.One2many(
        'salesperson.commission.line', 
        'parent_commission_id', 
        string='Installment Commissions'
    )
    vendor_bill_count = fields.Integer(
        string="Vendor Bill Count", 
        compute="_compute_vendor_bill_count"
    )
    existing_contract_ids = fields.Many2many(
        'ownership.contract', 
        compute='_compute_existing_contract_ids',
        string="Existing Contracts Dummy"
    )

    @api.depends('contract_id')
    def _compute_existing_contract_ids(self):
        # Fetch all contracts already assigned to a main commission line
        all_commissions = self.env['salesperson.commission.line'].search([
            ('parent_commission_id', '=', False)
        ])
        for rec in self:
            # Prevent the current record's contract from being filtered out
            rec_id = rec._origin.id if isinstance(rec.id, models.NewId) else rec.id
            excluded_commissions = all_commissions.filtered(lambda c: c.id != rec_id) if rec_id else all_commissions
            rec.existing_contract_ids = [(6, 0, excluded_commissions.mapped('contract_id').ids)]
        
    def _generate_installment_commissions(self):
        """Generate installment commission lines without calling write() on the parent."""
        Commission = self.env['salesperson.commission.line']

        for rec in self:
            if (
                rec.commission_release_policy != 'on_payment'
                or not rec.contract_id
                or rec.installment_commission_ids
            ):
                continue

            for installment in rec.contract_id.loan_line_rs_own_ids:
                Commission.with_context(
                    skip_installment_generation=True
                ).create({
                    'parent_commission_id': rec.id,
                    'sales_person': rec.sales_person.id,
                    'user_id': rec.user_id.id,
                    'installment_id': installment.id,
                    'contract_id': rec.contract_id.id,
                    'commission_percent': rec.commission_percent,
                    'amount_base': installment.amount,
                    'amount': installment.amount * rec.commission_percent / 100.0,
                    'commission_release_policy': 'on_payment',
                    'state': 'draft',
                    'company_id': rec.company_id.id,
                })

    @api.depends('vendor_bill_id', 'installment_commission_ids.vendor_bill_id')
    def _compute_vendor_bill_count(self):
        for rec in self:
            bill_ids = rec.vendor_bill_id.ids + rec.installment_commission_ids.mapped('vendor_bill_id').ids
            rec.vendor_bill_count = len(list(set(bill_ids)))

    def action_view_vendor_bill(self):
        self.ensure_one()
        # Collate all unique vendor bills from this line and its installments
        bill_ids = list(set(self.vendor_bill_id.ids + self.installment_commission_ids.mapped('vendor_bill_id').ids))
        
        if not bill_ids:
            raise UserError(_("No Vendor Bills are linked to this commission line."))

        action = {
            'name': _('Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }

        if len(bill_ids) == 1:
            # Return form view directly
            action.update({
                'view_mode': 'form',
                'res_id': bill_ids[0],
            })
        else:
            # Return list view
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', bill_ids)],
            })
            
        return action

    @api.depends('installment_id', 'contract_id')
    def _compute_amount_base(self):
        for rec in self:
            if rec.installment_id:
                rec.amount_base = rec.installment_id.amount
            elif rec.contract_id:
                rec.amount_base = rec.contract_id.amount_total
            else:
                rec.amount_base = 0

    @api.depends('amount_base', 'commission_percent')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.amount_base * rec.commission_percent / 100.0
        
    def action_confirm(self):
        for record in self:
            if not record.sales_person:
                raise UserError(_("Please select a Sales Person."))
            if not record.contract_id:
                raise UserError(_("Please select a Contract."))
            if record.commission_percent <= 0:
                raise UserError(_("Commission Percentage must be greater than zero."))
            record.state = 'confirmed'

    def action_set_to_draft(self):
        for record in self:
            if record.vendor_bill_id:
                raise UserError(_("You cannot reset this commission to Draft because a Vendor Bill already exists."))
            record.state = 'draft'
    def action_cancel(self):
        for record in self:
            if record.vendor_payment_id:
                raise UserError(_("You cannot cancel a commission that has already been paid."))
            record.state = 'cancelled'

    @api.onchange('contract_id', 'commission_percent', 'commission_release_policy')
    def _onchange_contract_or_policy(self):
        # Do not execute if we are currently saving / generating on the backend
        if self.env.context.get('skip_installment_generation'):
            return

        if self.commission_release_policy != 'on_payment' or not self.contract_id:
            self.installment_commission_ids = [(5, 0, 0)]
            return

        lines = []
        for installment in self.contract_id.loan_line_rs_own_ids:
            commission_amount = (installment.amount * self.commission_percent / 100.0)
            lines.append((0, 0, {
                'sales_person': self.sales_person.id,
                'user_id': self.user_id.id,
                'installment_id': installment.id,
                'contract_id': self.contract_id.id,
                'commission_percent': self.commission_percent,
                'amount_base': installment.amount,
                'amount': commission_amount,
                'commission_release_policy': 'on_payment',
                'state': 'draft',
            }))
        self.installment_commission_ids = lines

    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super(
    #         SalespersonCommissionLine,
    #         self.with_context(skip_installment_generation=True)
    #     ).create(vals_list)
    #     for record in records:
    #         if (
    #             record.commission_release_policy == 'on_payment'
    #             and record.contract_id
    #             and not record.parent_commission_id
    #         ):
    #             record._generate_installment_commissions()

    #     return records

    def write(self, vals):
        protected_fields = set(vals.keys()) - {'state'}

        for record in self:
            if record.state in ('confirmed', 'cancelled') and protected_fields:
                raise UserError(
                    _("You cannot modify a confirmed or cancelled commission.")
                )

        res = super().write(vals)

        if self.env.context.get('skip_installment_generation'):
            return res

        # trigger_fields = {
        #     'commission_release_policy',
        #     'contract_id',
        #     'commission_percent',
        # }

        # if trigger_fields.intersection(vals):
        #     for record in self:
        #         if record.parent_commission_id:
        #             continue
        #         if record.commission_release_policy == 'on_payment' and record.contract_id:
        #             record.installment_commission_ids.with_context(skip_installment_generation=True).unlink()
        #             # record._generate_installment_commissions()
        #         else:
        #             pass
                    # record.installment_commission_ids.with_context(skip_installment_generation=True).unlink()
        return res
    # def write(self, vals):
    #     protected_fields = set(vals.keys()) - {'state'}

    #     for record in self:
    #         if record.state in ('confirmed', 'cancelled') and protected_fields:
    #             raise UserError(
    #                 _("You cannot modify a confirmed or cancelled commission.")
    #             )

    #     return super().write(vals)
    def action_create_vendor_bill(self):
        self.ensure_one()
        # if self.state != 'confirmed':
        #     raise UserError(_("Only confirmed commissions can have a Vendor Bill created."))
        if not self.sales_person:
            raise UserError(_("Please assign a Sales Person first before creating a vendor bill."))
        if self.vendor_bill_id:
            raise UserError(_("A vendor bill has already been created for this commission line."))

        # Enforce current company context on bill creation
        company = self.company_id or self.env.company

        # Ensure correct import-free retrieval of localized context date
        today_date = fields.Date.context_today(self)

        invoice_lines = [{
            'name': _('Sales Commission - %s') % (self.contract_id.name or ""),
            'quantity': 1,
            'price_unit': self.amount,
        }]

        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.sales_person.id,
            'invoice_date': today_date,
            'invoice_origin': self.contract_id.name,
            'company_id': company.id,
            'invoice_line_ids': [(0, 0, line) for line in invoice_lines],
        }

        # Context passing avoids multi-company defaults hijacking
        bill = self.env['account.move'].with_company(company).create(bill_vals)
        self.vendor_bill_id = bill.id
        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': bill.id,
            'target': 'current',
        }

    


