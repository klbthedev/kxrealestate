from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CustomerPaymentRefund(models.TransientModel):
    _name = 'customer.payment.refund'

    account_id = fields.Many2one('account.account', string='Account')
    contract_id = fields.Many2one('ownership.contract', string='Ownership Contract', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    managerial_expenses = fields.Float(string='Managerial Expenses (Amt.)')
    managerial_expenses_percent = fields.Float(string='Managerial Expenses (%)')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    payment_method = fields.Selection([('cash', 'Cash'), ('cheque', 'Cheque')], string='Payment Method', default='cash', required=True)

    @api.onchange('managerial_expenses')
    def onchange_managerial_expenses(self):
        if self.managerial_expenses > 0:
            self.managerial_expenses_percent = 0

    @api.onchange('managerial_expenses_percent')
    def onchange_managerial_expenses_percent(self):
        if self.managerial_expenses_percent > 0:
            self.managerial_expenses = 0.0

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            contracts = []
            contract_ids = self.env['ownership.contract'].search([('partner_id', '=', self.partner_id.id), ('state', '=', 'confirmed')])
            for obj in contract_ids:
                contracts.append(obj.id)
            return {'domain': {'contract_id': [('id', 'in', contracts)]}}

    def create_voucher(self, rec, type, amt, date, name):
        voucher_obj = self.env['account.payment']
        payment_method = self.env.ref('account.account_payment_method_manual_out')
        vals = {
            'real_estate_ref': rec.contract_id.name,
            'journal_id': rec.journal_id.id,
            'payment_type': type,
            'payment_date': date,
            'amount': amt,
            'payment_method_id': payment_method.id,
            'partner_id': rec.contract_id.partner_id.id,
            'partner_type': 'customer',
            'communication': name,
        }
        voucher_id = voucher_obj.create(vals)
        return voucher_id

    def create_voucher_line(self, rec, voucher_id):
        voucher_line_obj = self.env['account.voucher.line']
        lines = self.env['loan.line.rs.own'].search([('loan_id', '=', rec.contract_id.id)])
        lines_ids = []
        for l in lines: lines_ids.append(l.id)
        loan_line_rs_own_obj = self.env['loan.line.rs.own'].browse(lines_ids)
        for line in loan_line_rs_own_obj:
            if line.paid:
                name = line.name + str('Installment Refund regarding ownership contract # ') + rec.contract.name
                voucher_line_obj.create({'voucher_id': voucher_id.id, 'name': name, 'price_unit': line.amount, 'account_id': rec.account.id})

    def apply_me(self, rec):
        total = 0
        for line in rec.contract_id.loan_line_rs_own_ids:
            if line.paid:
                total += line.amount
        me_expense = rec.managerial_expenses + (rec.managerial_expenses_percent * total / 100.0)
        expense_account_id = self.env['res.config.settings'].browse(
            self.env['res.config.settings'].search([])[-1].id).expense_account_id.id if self.env['res.config.settings'].search([]) else ""
        if not expense_account_id and me_expense:
            raise UserError(_('Please set default Managerial Expenses Account!'))
        if me_expense:
            today = date.today()
            voucher = self.create_voucher(self, 'outbound', me_expense, today, 'Managerial Expenses')
            return voucher.id

    def refund(self):
        for rec in self:
            contract = rec.contract_id
            any_paid = False
            for line in rec.contract_id.loan_line_rs_own_ids:
                if line.paid:
                    any_paid = True
                    break
            if not any_paid:
                raise UserError(_('You can just cancel contract, no payments to refund!'))
            journal_pool = self.env['account.journal']
            journal = journal_pool.search([('type', '=', 'purchase')], limit=1)
            today = fields.Date.context_today
            today = date.today()
            contract.write({'state': 'cancel'})
            if rec.payment_method == 'cash':
                if not journal:
                    raise UserError(_('Please set purchase accounting journal!'))
                lines = self.env['loan.line.rs.own'].search([('loan_id', '=', rec.contract_id.id)])
                lines_ids = []
                amt = 0.0
                for l in lines: lines_ids.append(l.id)
                loan_line_rs_own_obj = self.env['loan.line.rs.own'].browse(lines_ids)
                for line in loan_line_rs_own_obj:
                    if line.paid:
                        amt += line.amount
                name = str('Refund for ownership contract # ') + rec.contract_id.name
                voucher = self.create_voucher(self, 'outbound', amt, today, name)
                vouchers = [voucher.id]
                if self.apply_me(rec):
                    vouchers.append(self.apply_me(rec))
                return {
                    'name': _('Vouchers'),
                    'view_type': 'form',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', vouchers)],
                    'res_model': 'account.payment',
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'current',
                }
