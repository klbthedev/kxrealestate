import re
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ContractArticle(models.Model):
    _name = 'contract.article'
    _description = 'Contract Template Article'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    template_id = fields.Many2one(
        'contract.template', string='Template', 
        # ondelete='cascade',
          required=True, index=True)
    clause_ids = fields.One2many(
        'contract.clause', 'article_id', string='Clauses')
    clause_count = fields.Integer(compute='_compute_clause_count', string='Clauses')
    company_id = fields.Many2one(
        related='template_id.company_id', store=True, string='Company', readonly=True)

    @api.depends('clause_ids')
    def _compute_clause_count(self):
        for rec in self:
            rec.clause_count = len(rec.clause_ids)


class ContractClause(models.Model):
    _name = 'contract.clause'
    _description = 'Contract Article Clause'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Clause Title', required=True)
    body = fields.Html(string='Clause Body', sanitize=True, sanitize_attributes=False)
    mandatory = fields.Boolean(string='Mandatory', default=True)
    active = fields.Boolean(default=True)
    article_id = fields.Many2one(
        'contract.article', string='Article', 
        # ondelete='cascade', 
        required=True, index=True)
    template_id = fields.Many2one(
        related='article_id.template_id', string='Template', store=True, readonly=True)
    company_id = fields.Many2one(
        related='article_id.company_id', store=True, string='Company', readonly=True)


class ContractContract(models.Model):
    _name = 'contract.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'contract_date desc, id desc'

    reference = fields.Char(string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    template_id = fields.Many2one('contract.template', string='Template', required=True, tracking=True,domain=[('state', '=', 'approved')])
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,required=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Review'),
        ('approved', 'Approved'),
        ('signed', 'Signed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True, copy=False, index=True)

    contract_date = fields.Date(string='Contract Date', default=fields.Date.context_today, tracking=True)
    effective_date = fields.Date(string='Effective Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    generated_html = fields.Html(string='Generated HTML', sanitize=False, readonly=True, copy=False)
    generated_pdf = fields.Binary(string='Generated PDF', readonly=True, copy=False, attachment=True)
    generated_pdf_name = fields.Char(string='PDF Filename', readonly=True, copy=False)
    articles_snapshot = fields.Html(string='Articles Snapshot', sanitize=False, readonly=True, copy=False,
        help='Frozen copy of the template articles/clauses raw HTML at the '
             'moment the contract was created, so future template edits do '
             'not retroactively change existing contracts.')
    clauses_snapshot = fields.Text(string='Clauses Snapshot (JSON)', readonly=True, copy=False)
    expiring_soon = fields.Boolean(compute='_compute_expiring_soon', string='Expiring Soon', store=True)
    is_expired = fields.Boolean(compute='_compute_expiring_soon', string='Expired', store=True)
    activity_history_count = fields.Integer(compute='_compute_activity_history_count', string='Activities')
    _sql_constraints = [
        ('reference_uniq', 'unique(reference, company_id)',
         'Contract reference must be unique per company.'),
    ]

    @api.depends('expiry_date', 'state')
    def _compute_expiring_soon(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=30)
        for rec in self:
            rec.is_expired = bool(rec.expiry_date and rec.expiry_date < today and rec.state not in ('cancelled', 'archived'))
            rec.expiring_soon = bool(rec.expiry_date and today <= rec.expiry_date <= soon and rec.state not in ('cancelled', 'archived'))

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
        self._sync_variable_values()
        return True

    def _get_render_values(self):
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
        report = self.env.ref('kx_realestate.action_report_contract')
        pdf_content, _fmt = report._render_qweb_pdf([self.id])
        self.generated_pdf = pdf_content and __import__('base64').b64encode(pdf_content)
        self.generated_pdf_name = '%s.pdf' % (self.reference or 'Contract')

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('kx_realestate.action_report_contract').report_action(self)

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
            'kx_realestate.mail_template_contract_expiry_reminder', raise_if_not_found=False)
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


class ContractTemplate(models.Model):
    _name = 'contract.template'
    _description = 'Contract Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name, version desc'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False, tracking=True)
    version = fields.Char(string='Version', default='1.0', tracking=True)
    description = fields.Text(string='Description')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
        required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ], string='State', default='draft', tracking=True, copy=False)

    article_ids = fields.One2many(
        'contract.article', 'template_id', string='Articles')
    variable_ids = fields.One2many(
        'contract.variable', 'template_id', string='Variables')

    article_count = fields.Integer(compute='_compute_counts', string='Articles')
    variable_count = fields.Integer(compute='_compute_counts', string='Variables')
    contract_count = fields.Integer(compute='_compute_counts', string='Contracts')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Template code must be unique per company.'),
    ]

    @api.depends('article_ids', 'variable_ids')
    def _compute_counts(self):
        Contract = self.env['contract.contract']
        contract_data = {}
        if self.ids:
            grouped = Contract.read_group(
                [('template_id', 'in', self.ids)], ['template_id'], ['template_id'])
            contract_data = {g['template_id'][0]: g['template_id_count'] for g in grouped}
        for rec in self:
            rec.article_count = len(rec.article_ids)
            rec.variable_count = len(rec.variable_ids)
            rec.contract_count = contract_data.get(rec.id, 0)

    def action_approve(self):
        for rec in self:
            if not rec.article_ids:
                raise UserError(_('Cannot approve a template without any Articles.'))
            rec.state = 'approved'

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_archive_template(self):
        self.write({'state': 'archived', 'active': False})

    def action_view_contracts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'kx_realestate.action_contract_contract')
        action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def action_view_articles(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'kx_realestate.action_contract_article')
        action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def action_view_variables(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'kx_realestate.action_contract_variable')
        action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def get_combined_html(self):
        self.ensure_one()
        parts = []
        for article in self.article_ids.filtered('active').sorted('sequence'):
            parts.append('<h2 class="contract_article_title">%s</h2>' % (article.name or ''))
            if article.description:
                parts.append('<p class="contract_article_description">%s</p>' % (article.description or ''))
            for clause in article.clause_ids.filtered('active').sorted('sequence'):
                parts.append('<h4 class="contract_clause_title">%s</h4>' % (clause.name or ''))
                parts.append(clause.body or '')
        return ''.join(parts)

class ContractVariable(models.Model):
    _name = "contract.variable"
    _description = "Contract Variable"
    _order = "sequence,id"

    name = fields.Char(required=True)

    code = fields.Char(required=True,help="Use inside clauses as {{Code}}",)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    template_id = fields.Many2one(
        "contract.template",
        required=True,
        # ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="template_id.company_id",
        store=True,
        readonly=True,
    )
    active = fields.Boolean(default=True)
    required = fields.Boolean(default=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        help="Root model for this variable.",
    )

    field_id = fields.Many2one(
        "ir.model.fields",
        string="Field Path",
        required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id)]",
        help="Select the field to use in the contract.",
    )
    example_value = fields.Char()
    _sql_constraints = [
        (
            "code_template_unique",
            "unique(code,template_id)",
            "Variable Code must be unique.",
        )
    ]

    def _get_field_path_selection(self):
        selections = []
        for rec in self:
            if not rec.model_id:
                continue
            model = self.env[rec.model_id.model]
            selections.extend(self._get_model_fields(model))
        return selections

    def _get_model_fields(self, model, prefix="", depth=2):
        result = []
        if depth <= 0:
            return result
        for field_name, field in model._fields.items():
            if field_name.startswith("_"):
                continue
            path = (
                f"{prefix}.{field_name}"
                if prefix
                else field_name
            )
            if field.type not in ("one2many", "many2many"):
                result.append((path,path))
            if field.type == "many2one":
                result.extend(self._get_model_fields(self.env[field.comodel_name],path,depth - 1))
        return result

    @api.constrains("code")
    def _check_code(self):
        regex = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        for rec in self:
            if not regex.match(rec.code):
                raise ValidationError(_("Variable Code is invalid."))
            
    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.field_id = False


class ContractFieldResolver(models.AbstractModel):

    _name = "contract.field.resolver"
    
    def resolve_field(self, record, field):
        value = record
        for part in field.split("."):
            if not value:
                return ""
            value = value[part]
        if value is False or value is None:
            return ""
        if hasattr(value, "display_name"):
            return value.display_name

        return str(value)