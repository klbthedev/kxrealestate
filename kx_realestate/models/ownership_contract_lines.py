from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
import requests
import logging

_logger = logging.getLogger(__name__)

class RealEstateCommunicationMethod(models.Model):
    _name = 're.communication.method'
    _description = 'Real Estate Communication Method'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('re_communication_method_code_uniq', 'unique(code)', 'Communication method code must be unique.'),
    ]


class OwnershipBuyerResponsibility(models.Model):
    _name = 'ownership.buyer.responsibility'
    _description = 'Ownership Buyer Responsibility'
    _order = 'sequence, id'

    ownership_contract_id = fields.Many2one('ownership.contract', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Responsibility', required=True)
    done = fields.Boolean(default=False)


class OwnershipSellerResponsibility(models.Model):
    _name = 'ownership.seller.responsibility'
    _description = 'Ownership Seller/Builder Responsibility'
    _order = 'sequence, id'

    ownership_contract_id = fields.Many2one('ownership.contract', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Responsibility', required=True)
    done = fields.Boolean(default=False)


class OwnershipHandoverChecklist(models.Model):
    _name = 'ownership.handover.checklist'
    _description = 'Ownership Handover Checklist'
    _order = 'sequence, id'

    ownership_contract_id = fields.Many2one('ownership.contract', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Checklist Item', required=True)
    checklist_type = fields.Selection(
        [('common', 'Common'), ('individual', 'Individual')],
        default='common',
        required=True,
    )
    done = fields.Boolean(default=False)
    is_fully_paid = fields.Boolean(
        related='ownership_contract_id.is_fully_paid',
        string='Fully Paid',
        store=True
    )


class OwnershipTermPenaltyRule(models.Model):
    _name = 'ownership.term.penalty.rule'
    _description = 'Ownership Terms and Penalty Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    ownership_contract_id = fields.Many2one('ownership.contract', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    rule_scope = fields.Selection(
        [('custom', 'Custom'), ('sample', 'Sample Logic')],
        default='custom',
        required=True,
        index=True,
    )
    clause_ref = fields.Char(string='Clause Ref')
    rule_text = fields.Char(string='Rule', required=True)
    applies_to = fields.Selection(
        [('buyer', 'Buyer'), ('developer', 'Developer'), ('both', 'Both')],
        default='buyer',
        required=True,
    )
    action_type = fields.Selection(
        [
            ('payment', 'Payment'),
            ('notice', 'Notice'),
            ('refund', 'Refund'),
            ('terminate', 'Terminate Contract'),
            ('info', 'Informational'),
        ],
        default='info',
        required=True,
    )
    evaluation_snapshot = fields.Char(string='Evaluation Snapshot', readonly=True)
    rule_met = fields.Boolean(string='Rule Met', compute='_compute_rule_met', store=True)
    trigger_hit = fields.Boolean(string='Trigger Hit', readonly=False)

    model_field_id = fields.Many2one(
        'ir.model.fields',
        string='Contract Field',
        domain="[('model', '=', 'ownership.contract')]",
        ondelete='cascade',
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model',
        ondelete='cascade',
        default=lambda self: self.env['ir.model']._get('ownership.contract')
        )
    condition_domain = fields.Char(
        string='Advanced Domain',
        default='[]',
        help='Advanced mode: domain evaluated against ownership.contract record.',
    )
    domain_model = fields.Char(default='ownership.contract', readonly=True)
    field_name = fields.Char(related='model_field_id.name', string='Field Name', readonly=True)
    field_type = fields.Selection(related='model_field_id.ttype', string='Field Type', readonly=True)
    condition_operator = fields.Selection(
        [
            ('=', '='),
            ('!=', '!='),
            ('>', '>'),
            ('>=', '>='),
            ('<', '<'),
            ('<=', '<='),
            ('set', 'Is Set'),
            ('not_set', 'Is Not Set'),
            ('contains', 'Contains'),
        ],
        string='Condition',
        default='=',
        required=True,
    )
    condition_value = fields.Char(
        string='Condition Value',
        help='Value to compare against. Keep in text form for flexibility across field types.',
    )
    logic_joiner = fields.Selection(
        [('and', 'AND'), ('or', 'OR')],
        string='Apply Logic',
        default='and',
        required=True,
        help='How this line combines with next line(s).',
    )

    @api.depends('trigger_hit')
    def _compute_rule_met(self):
        for rec in self:
            rec.rule_met = rec.trigger_hit

    def _matches_contract_domain(self, contract):
        self.ensure_one()
        if not self.condition_domain:
            self.trigger_hit = False
            return False
        try:
            domain = safe_eval(self.condition_domain, {})
        except Exception:
            self.trigger_hit = False
            return False
        if not isinstance(domain, list):
            self.trigger_hit = False
            return False
        records = self.env['ownership.contract'].search(domain)
        match = contract in records
        if match:
            fields_used = [d[0] for d in domain if isinstance(d, (list, tuple)) and len(d) >= 3]
            self.evaluation_snapshot = f"Matched fields: {', '.join(fields_used)}"
        else:
            self.evaluation_snapshot = "No match"
        self.trigger_hit = match
        return match

    def action_notify_user(self):
        self.ensure_one()
        contract = self.ownership_contract_id
        user = self.env.user
        contracts = self.env['ownership.contract'].browse([contract.id])
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('ownership.contract').id,
            'res_id': contract.id,
            'user_id': user.id,
            'activity_type_id': activity_type.id,
            'summary': f"Penalty Rule Triggered: {self.rule_text}",
            'note': f"The rule {self.rule_text} has been triggered for {contract.name}.",
            'automated': True,
        })
        return {
            'name': 'Triggered Contracts',
            'type': 'ir.actions.act_window',
            'res_model': 'ownership.contract',
            'view_mode': 'list,form',
            # 'views': [(self.env.ref('kx_realestate.ownership_contract_tree_view').id, 'list')],
            'domain': [('id', 'in', contracts.ids)],
            'target': 'current',
        }
    
    def _normalize_phone_number(self, phone: str) -> str:
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = "251" + phone[1:]
        elif phone.startswith("+251"):
            phone = "251" + phone[4:]
        elif not phone.startswith("2519"):
            phone = "2519" + phone[-8:]
        return phone

    @api.model
    def send_sms(self, phone: str, message: str) -> bool:
        _logger.info("[SMS] Sending SMS to %s", phone)
        try:
            geezsms_token = self.env['ir.config_parameter'].sudo().get_param('geezsms.token')
            geezsms_shortcode_id = self.env['ir.config_parameter'].sudo().get_param('geezsms.shortcode_id')
            api_url = self.env['ir.config_parameter'].sudo().get_param('geezsms.sms_endpoint')
            if not geezsms_token:
                _logger.error("GeezSMS token is not configured")
                raise UserError(_("GeezSMS token is not configured."))
            normalized_phone = self._normalize_phone_number(phone)
            payload = {'token': geezsms_token, 'phone': normalized_phone, 'msg': message}
            if geezsms_shortcode_id:
                payload['shortcode_id'] = geezsms_shortcode_id
            import requests, pprint
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                _logger.info(f"[SMS] Sent SMS to {normalized_phone}")
                return True
            else:
                _logger.error(f"[SMS] Failed {response.status_code}: {response.text}")
                return False
        except Exception as e:
            _logger.error(f"[SMS] Error sending SMS: {str(e)}")
            return False

    def action_send_sms(self):
        for rec in self.filtered('trigger_hit'):
            message = f"Rule triggered: {rec.rule_text} on contract {rec.ownership_contract_id.name}"
            # send to creator
            rec.send_sms(rec.create_uid.partner_id.phone, message)
            # send to buyer if applies_to
            contract = rec.ownership_contract_id
            if rec.applies_to in ['buyer', 'both']:
                if contract.phone:
                    rec.send_sms(contract.phone, message)
                if contract.signed_by_other_phone:
                    rec.send_sms(contract.signed_by_other_phone, message)

    def action_evaluate_rule(self):
        for rec in self:
            contract = rec.ownership_contract_id
            rec._matches_contract_domain(contract)
            rec.action_notify_user()
            rec.action_send_sms()

    def action_evaluate_all_rules(self):
        rules = self.search([])
        for rule in rules:
            rule.action_evaluate_rule()

