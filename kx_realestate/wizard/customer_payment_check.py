from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CustomerPaymentCheck(models.TransientModel):
    _name = 'customer.payment.check'

    account_id = fields.Many2one('account.account', string='Account')
    contract_id = fields.Many2one('ownership.contract', string='Ownership Contract', required=True)
    cheque_number = fields.Char(string='Reference')
    discount_cash_total = fields.Float(string='Discount (Amt.)')
    discount_percent_total = fields.Float(string='Discount %')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    loan_line_ids = fields.One2many('loan.line.rs.wizard', 'loan_id')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    payment_method = fields.Selection([('cash','Cash'),('cheque','Cheque')], string='Payment Method', default='cash', required=True)
    select_all = fields.Boolean(string='Select all')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        contract_id = self.env.context.get('default_contract_id')
        if contract_id and not res.get('contract_id'):
            contract = self.env['ownership.contract'].browse(contract_id)
            if contract:
                res['contract_id'] = contract.id
                res['partner_id'] = contract.partner_id.id
                loan_lines = []
                for line in contract.loan_line_rs_own_ids:
                    if line.total_remaining_amount:
                        loan_lines.append((0, 0, {
                            'date': line.date,
                            'amount': line.total_remaining_amount,
                            'installment_line_id': line.id,
                            'name': line.name,
                        }))
                res['loan_line_ids'] = loan_lines
        return res

    @api.onchange('contract_id')
    def onchange_contract(self):
        self.loan_line_ids=None
        if self.contract_id:
            loan_lines=[]
            for line in self.contract_id.loan_line_rs_own_ids:
                if line.total_remaining_amount:
                    loan_lines.append((0,0,{'date':line.date,'amount':line.total_remaining_amount,'installment_line_id': line.id, 'name':line.name}))
            self.partner_id=self.contract_id.partner_id.id
            self.loan_line_ids=loan_lines

    @api.onchange('select_all')
    def onchange_select(self):
        self.loan_line_ids=None
        if self.contract_id:
            loan_lines=[]
            for line in self.contract_id.loan_line_rs_own_ids:
                if line.total_remaining_amount:
                    if self.select_all:
                        loan_lines.append((0,0,{'to_be_paid':True, 'date':line.date,'amount':line.total_remaining_amount,'installment_line_id': line.id, 'name':line.name}))
                    else:
                        loan_lines.append((0,0,{'to_be_paid':False, 'date':line.date,'amount':line.total_remaining_amount,'installment_line_id': line.id, 'name':line.name}))
            self.loan_line_ids = loan_lines

    @api.onchange('discount_cash_total')
    def onchange_discount_cash(self):
        if self.discount_cash_total>0:
            self.discount_percent_total = 0.0

    @api.onchange('discount_percent_total')
    def onchange_discount_percent(self):
        if self.discount_percent_total>0:
            self.discount_cash_total = 0.0

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            contracts=[]
            contract_ids = self.env['ownership.contract'].search([('partner_id', '=', self.partner_id.id),('state','=','confirmed')])
            for contract in contract_ids:
                contracts.append(contract.id)
            return {'domain': {'contract_id': [('id', 'in', contracts)]}}

    def create_voucher(self, rec, type, amt, date, name, partner_type, line_id=False, ):
        voucher_obj = self.env['account.payment']
        if partner_type=='customer':
            payment_method= self.env.ref('account.account_payment_method_manual_out')
        else:
            payment_method= self.env.ref('account.account_payment_method_manual_in')
        vals= {
            'loan_line_rs_own_id': line_id,
            'real_estate_ref': rec.contract_id.name,
            'journal_id': rec.journal_id.id,
            'payment_type': type,
            'date': date,
            'amount': amt,
            'payment_method_id': payment_method.id,
            'partner_id': rec.contract_id.partner_id.id,
            'partner_type': partner_type,
            'ref': name,
        }
        voucher_id = voucher_obj.create(vals)
        return voucher_id

    def apply_discount(self, rec):
        lines_discount=0
        total_amount=0
        for line in rec.loan_line_ids:
            if line.to_be_paid:
                lines_discount += (line.amount*line.discount_percent)/100.0+line.discount_cash
                total_amount+=line.amount
        total_discount = total_amount*rec.discount_percent_total/100.0 + rec.discount_cash_total
        total_discount += lines_discount

        if total_discount > 0:
            dt= fields.Date.today()
            voucher = self.create_voucher(self, 'outbound', total_discount, dt, 'Allowed Discount','supplier')
            return voucher

    def pay(self):
        penalty_obj = self.env['late.payment.penalties']
        vouchers = []
        today = str(fields.Date.context_today)
        total_penalties = 0
        if self.payment_method=='cash':
            for line in self.loan_line_ids:
                if line.to_be_paid:
                    total_penalties+=penalty_obj.get_penalties(line)
                    installment_line_id= line.installment_line_id
                    if installment_line_id:
                        if not self.contract_id.partner_id.property_account_receivable_id.id:
                            raise UserError(_('Please set receivable account for Partner'))
                        loan_line_rs_own_obj = self.env['loan.line.rs.own'].browse(installment_line_id)
                        for line1 in loan_line_rs_own_obj:
                            amt = line.amount
                            dt = line1.date
                            name=str(' Regarding Ownership Contract ')+str(self.contract_id.name)
                            payments = line1.register_customer_payment_via_invoice(
                                amount=amt,
                                payment_date=dt,
                                journal=self.journal_id,
                                communication=name,
                            )
                            vouchers.extend(payments.ids)
                        discount_voucher= self.apply_discount(self)
                        if discount_voucher:
                            vouchers.append(discount_voucher.id)
                        if total_penalties>0:
                            penalty_str=str(' Penalty on Ownership Contract ')+str(self.contract_id.name)
                            v= self.create_voucher(self, 'inbound', total_penalties, today, penalty_str, 'customer')
                            vouchers.append(v.id)
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
