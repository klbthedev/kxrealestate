# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractContract(models.Model):
    _name = 'contract.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'contract_date desc, id desc'

    reference = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True)
    template_id = fields.Many2one(
        'contract.template', string='Template', required=True, tracking=True,
        domain=[('state', '=', 'approved')])
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
        required=True)
    user_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Review'),
        ('approved', 'Approved'),
        ('signed', 'Signed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True, copy=False, index=True)

    contract_date = fields.Date(
        string='Contract Date', default=fields.Date.context_today, tracking=True)
    effective_date = fields.Date(string='Effective Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)

    generated_html = fields.Html(
        string='Generated HTML', sanitize=False, readonly=True, copy=False)
    generated_pdf = fields.Binary(string='Generated PDF', readonly=True, copy=False, attachment=True)
    generated_pdf_name = fields.Char(string='PDF Filename', readonly=True, copy=False)

    variable_value_ids = fields.One2many(
        'contract.variable.value', 'contract_id', string='Variable Values', copy=True)

    articles_snapshot = fields.Html(
        string='Articles Snapshot', sanitize=False, readonly=True, copy=False,
        help='Frozen copy of the template articles/clauses raw HTML at the '
             'moment the contract was created, so future template edits do '
             'not retroactively change existing contracts.')
    clauses_snapshot = fields.Text(
        string='Clauses Snapshot (JSON)', readonly=True, copy=False)

    expiring_soon = fields.Boolean(compute='_compute_expiring_soon', string='Expiring Soon', store=True)
    is_expired = fields.Boolean(compute='_compute_expiring_soon', string='Expired', store=True)

    activity_history_count = fields.Integer(
        compute='_compute_activity_history_count', string='Activities')

    _sql_constraints = [
        ('reference_uniq', 'unique(reference, company_id)',
         'Contract reference must be unique per company.'),
    ]

    @api.depends('expiry_date', 'state')
    def _compute_expiring_soon(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=30)
        for rec in self:
            rec.is_expired = bool(rec.expiry_date and rec.expiry_date < today
                                   and rec.state not in ('cancelled', 'archived'))
            rec.expiring_soon = bool(rec.expiry_date and today <= rec.expiry_date <= soon
                                      and rec.state not in ('cancelled', 'archived'))

    def _compute_activity_history_count(self):
        for rec in self:
            rec.activity_history_count = self.env['mail.message'].search_count(
                [('res_id', '=', rec.id), ('model', '=', self._name)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'contract.contract') or _('New')
        records = super().create(vals_list)
        for rec in records:
            rec._sync_variable_values()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'template_id' in vals:
            for rec in self:
                rec._sync_variable_values()
        return res

    def _sync_variable_values(self):
        """Ensure a contract.variable.value line exists for every variable
        defined on the selected template (creates missing lines, leaves
        existing ones untouched, removes lines for variables no longer on
        the template).
        """
        for rec in self:
            if not rec.template_id:
                continue
            existing = {line.variable_id.id: line for line in rec.variable_value_ids}
            template_var_ids = rec.template_id.variable_ids.ids
            to_create = []
            for variable in rec.template_id.variable_ids:
                if variable.id not in existing:
                    to_create.append({
                        'contract_id': rec.id,
                        'variable_id': variable.id,
                        'value_char': variable.default_value or False,
                    })
            if to_create:
                self.env['contract.variable.value'].create(to_create)
            obsolete = rec.variable_value_ids.filtered(
                lambda l: l.variable_id.id not in template_var_ids)
            obsolete.unlink()

    def action_get_default_variables(self):
        """Manual trigger (button/onchange helper) to (re)build variable value
        lines from the selected template."""
        self._sync_variable_values()
        return True

    def _get_render_values(self):
        """Build the {code: display_value} dict used by the renderer service,
        plus automatic system variables (Today, Company, PartnerName, ...).
        """
        self.ensure_one()
        values = {}
        for line in self.variable_value_ids:
            values[line.variable_id.code] = line.get_display_value()
        values.setdefault('PartnerName', self.partner_id.name or '')
        values.setdefault('Address', self.partner_id.contact_address or '')
        values.setdefault('Company', self.company_id.name or '')
        values.setdefault('ContractDate', fields.Date.to_string(self.contract_date) if self.contract_date else '')
        values.setdefault('Today', fields.Date.to_string(fields.Date.context_today(self)))
        return values

    def action_generate_preview(self):
        """Regenerate generated_html from the template + current variable values."""
        renderer = self.env['contract.template.renderer']
        for rec in self:
            if not rec.template_id:
                continue
            source_html = rec.articles_snapshot or rec.template_id.get_combined_html()
            values = rec._get_render_values()
            rec.generated_html = renderer.render(source_html, values)
        return True

    def get_live_preview_html(self, override_values=None):
        """RPC-friendly method: render a preview without persisting values,
        used by the OWL live preview widget while the user is still typing.
        override_values: dict {variable_code: raw_value} to use instead of
        the currently stored values (not yet saved to DB).
        """
        self.ensure_one()
        renderer = self.env['contract.template.renderer']
        source_html = self.articles_snapshot or (self.template_id and self.template_id.get_combined_html()) or ''
        values = self._get_render_values()
        if override_values:
            values.update(override_values)
        return renderer.render(source_html, values)

    def action_submit_review(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft contracts can be submitted for review.'))
            rec._check_required_variables()
            rec.action_generate_preview()
            rec.articles_snapshot = rec.template_id.get_combined_html()
            rec.state = 'review'
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Review Contract %s') % rec.reference,
                user_id=rec.user_id.id)

    def action_approve(self):
        for rec in self:
            if rec.state != 'review':
                raise UserError(_('Only contracts in Review can be approved.'))
            rec.action_generate_preview()
            rec.state = 'approved'

    def action_reject(self):
        for rec in self:
            if rec.state not in ('review', 'approved'):
                raise UserError(_('Only contracts in Review or Approved can be rejected.'))
            rec.state = 'draft'
            rec.message_post(body=_('Contract rejected and sent back to Draft.'))

    def action_sign(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Only approved contracts can be signed.'))
            rec.action_generate_preview()
            rec._generate_pdf()
            rec.state = 'signed'
            if not rec.effective_date:
                rec.effective_date = fields.Date.context_today(rec)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'signed':
                raise UserError(_('A signed contract cannot be cancelled, archive it instead.'))
            rec.state = 'cancelled'

    def action_archive_contract(self):
        self.write({'state': 'archived'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def _check_required_variables(self):
        for rec in self:
            missing = rec.variable_value_ids.filtered(
                lambda l: l.required and not l.get_display_value())
            if missing:
                raise ValidationError(_(
                    'Please fill in the following required variables before '
                    'continuing: %s') % ', '.join(missing.mapped('variable_id.name')))

    def _generate_pdf(self):
        self.ensure_one()
        report = self.env.ref('contract_management.action_report_contract')
        pdf_content, _fmt = report._render_qweb_pdf([self.id])
        self.generated_pdf = pdf_content and __import__('base64').b64encode(pdf_content)
        self.generated_pdf_name = '%s.pdf' % (self.reference or 'Contract')

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('contract_management.action_report_contract').report_action(self)

    def action_view_pdf_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'domain': [('res_id', '=', self.id), ('model', '=', self._name)],
            'name': _('PDF / Activity History'),
        }

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/contracts/%s' % rec.id

    @api.model
    def _cron_notify_expiring_contracts(self):
        soon = self.search([('expiring_soon', '=', True), ('state', 'not in', ['cancelled', 'archived'])])
        template = self.env.ref(
            'contract_management.mail_template_contract_expiry_reminder', raise_if_not_found=False)
        for rec in soon:
            if template:
                template.send_mail(rec.id, force_send=False)
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Contract %s is expiring soon') % rec.reference,
                user_id=rec.user_id.id)

    @api.model
    def _cron_archive_expired_contracts(self):
        expired = self.search([('is_expired', '=', True), ('state', 'not in', ['cancelled', 'archived'])])
        expired.write({'state': 'archived'})
