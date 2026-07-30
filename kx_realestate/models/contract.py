import re
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class ContractArticle(models.Model):
    _name = 'contract.article'
    _description = 'Contract Template Article'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    template_id = fields.Many2one(
        'contract.template',
        required=True,
        ondelete='cascade',
    )
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
        'contract.article',
        required=True,
        ondelete='cascade',
        domain="[('template_id', '=', template_id)]",
    )
    template_id = fields.Many2one(
        related='article_id.template_id', string='Template', store=True, readonly=True)
    company_id = fields.Many2one(
        related='article_id.company_id', store=True, string='Company', readonly=True)
    template_id = fields.Many2one(
        'contract.template',
        string='Template',
        required=True,
        index=True,
    )


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
    code = fields.Char(string='Code', required=False, copy=False, tracking=True)
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
    type = fields.Selection([
        ('amendment', 'Amendment'),
        ('contract', 'Contact'),
        
        ]
    )

    article_ids = fields.One2many(
        'contract.article', 'template_id', string='Articles')
    variable_ids = fields.One2many(
        'contract.variable', 'template_id', string='Variables')

    article_count = fields.Integer(compute='_compute_counts', string='Articles')
    variable_count = fields.Integer(compute='_compute_counts', string='Variables')
    contract_count = fields.Integer(compute='_compute_counts', string='Contracts')

    clause_ids = fields.One2many(
        'contract.clause',
        'template_id',
        string='Clauses',
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Template code must be unique per company.'),
    ]

    @api.depends('article_ids.clause_ids')
    def _compute_clause_ids(self):
        for rec in self:
            rec.clause_ids = rec.article_ids.mapped('clause_ids')

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
        parts.append('<h1 class="contract_title">%s</h1>' % (self.name or ''))
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

class ContractMaker(models.Model):
    _name = "contract.maker"
    _description = "Contract Maker"
    _rec_name = 'origin'

    name = fields.Char(required=True)
    origin = fields.Char(string='Source Document')
    contract_maker_type = fields.Selection(
        [
            ('reservation', 'Reservation Contract'),
            ('amendment', 'Amendment Contract'),
            ('sales_contract', 'Sales Contract'),
         ],
    )
    contract_template_id = fields.Many2one("contract.template")
    user_id = fields.Many2one("res.users")
    partner_id = fields.Many2one("res.partner")

    site_id = fields.Many2one("re.site")
    block_id = fields.Many2one("re.block")
    building_id = fields.Many2one("building.building")
    floor_id = fields.Many2one("re.floor")
    building_unit_id = fields.Many2one("product.template")

    selling_price = fields.Float()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('archived', 'Archived'),
            ('cancelled', 'Cancelled'), 
         ],
        default='draft'
    )
    ownership_contract_ids = fields.One2many(
        "ownership.contract",
        "contract_maker_id",
        string="Ownership Contract",
    )

    installment_line_ids = fields.One2many(
        "contract.maker.installment",
        "maker_id",
        string="Installments",
    )

    handover_ids = fields.One2many(
        "handover.checklist",
        "maker_id",
        string="Terms and Penality Rules",
    )
    penality_ids = fields.One2many(
        "term.penalty.rule",
        "maker_id",
        string="Hand Over Checklist",
    )
    generated_html = fields.Html(
        string="Generated Contract",
        sanitize=False,
        copy=False,
        store=True,
    )
    template_id = fields.Many2one(
        "contract.maker",
        required=False,
        ondelete="cascade",
    )
    article_ids = fields.One2many(
        "contract.maker.article",
        "maker_id",
        string="Articles",
    )
    variable_ids = fields.One2many(
        "contract.maker.variable",
        "maker_id",
        string="Variables",
    )
    clause_ids = fields.One2many(
        "contract.maker.clause",
        "maker_id",
        string="Clauses",
    )
# Amendment fields
    parent_id = fields.Many2one(
        "contract.maker",
        string="Parent Contract",
        ondelete="cascade",
    )

    amendment_ids = fields.One2many(
        "contract.maker",
        "parent_id",
        string="Amendments",
    )

    amendment_count = fields.Integer(
        compute="_compute_amendment_count",
    )

    is_amendment = fields.Boolean(
        compute="_compute_is_amendment",
        store=True,
    )
    amendment_no = fields.Integer(
        string="Amendment No.",
        compute="_compute_amendment_no",
        store=True,
    )
    
    @api.depends("parent_id")
    def _compute_is_amendment(self):
        for rec in self:
            rec.is_amendment = bool(rec.parent_id)

    @api.depends("parent_id", "parent_id.amendment_ids")
    def _compute_amendment_no(self):
        for rec in self:
            rec.amendment_no = 0
            if not rec.parent_id:
                continue
            siblings = rec.parent_id.amendment_ids.sorted(key=lambda r: (r.create_date or fields.Datetime.now(), r.id or 0))
            for index, amendment in enumerate(siblings, start=1):
                if amendment == rec:
                    rec.amendment_no = index
                    break

    @api.depends("amendment_ids")
    def _compute_amendment_count(self):
        for rec in self:
            rec.amendment_count = len(rec.amendment_ids)

    # Constraints
    @api.constrains("parent_id")
    def _check_parent(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.parent_id:
                raise ValidationError(_("An amendment cannot have another amendment as its parent."))

    # Actions
    def action_create_amendment(self):
        self.ensure_one()

        amendment = self.copy({
            "name": "%s - Amendment" % self.origin,
            "parent_id": self.id,
            "contract_maker_type": "amendment",
            "state": "draft",
        })

        return {
            "name": _("Amendment"),
            "type": "ir.actions.act_window",
            "res_model": "contract.maker",
            "view_mode": "form",
            "res_id": amendment.id,
            "target": "current",
        }

    def action_view_amendments(self):
        self.ensure_one()

        return {
            "name": _("Amendments"),
            "type": "ir.actions.act_window",
            "res_model": "contract.maker",
            "view_mode": "tree,form",
            "domain": [("parent_id", "=", self.id)],
            "context": {
                "default_parent_id": self.id,
                "default_contract_maker_type": "amendment",
            },
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def get_root_contract(self):
        self.ensure_one()

        contract = self
        while contract.parent_id:
            contract = contract.parent_id

        return contract

    def get_contract_title(self):
        self.ensure_one()

        if self.parent_id:
            return "%s - Amendment #%s" % (
                self.parent_id.origin,
                self.amendment_no,
            )

        return self.origin


# ///////////////
    def action_confirm(self):
        self.write({
            "state": "confirmed",
        })
    def action_reset_to_draft(self):
        self.write({
            "state": "draft",
        })
    
    @api.onchange('variable_ids', 'article_ids', 'clause_ids')
    def _update_generated_html(self):
        for rec in self:
            rec.generated_html = rec._render_contract_html()

    def _get_render_values(self):
        self.ensure_one()
        resolver = self.env["contract.field.resolver"]
        values = {}
        for variable in self.variable_ids.filtered("active"):
            values[variable.code] = resolver.resolve_field(self, variable.field_id.name,)
        return values
    def _render_contract_html(self):
        self.ensure_one()
        parts = []
        parts.append('<h1 class="contract_title">%s</h1>' % (self.origin or ""))
        for article in self.article_ids.filtered("active").sorted("sequence"):
            parts.append('<h2 class="contract_article_title">%s</h2>' % (article.name or ""))
            if article.description:
                parts.append('<p class="contract_article_description">%s</p>' % (article.description or ""))
            for clause in article.clause_ids.filtered("active").sorted("sequence"):
                parts.append('<h4 class="contract_clause_title">%s</h4>' % (clause.name or ""))
                parts.append(clause.body or "")
        html = "".join(parts)
        values = self._get_render_values()
        for key, value in values.items():
            html = html.replace("{{%s}}" % key, str(value or ""))
        return html
    
    @api.onchange('building_unit_id')
    def onchange_units(self):
        if self.building_unit_id:
            unit = self.building_unit_id
            self.floor_id = unit.floor
            self.selling_price = unit.selling_price
            self.building_id = unit.building_id.id
        else:
            self.floor_id = False
            self.selling_price = False
            self.building_id = False


    @api.constrains('installment_line_ids', 'selling_price')
    def _check_totals_warning(self):
        for rec in self:
            if not rec.installment_line_ids:
                continue
            expected_total = rec.selling_price or 0.0
            calculated_original_total = sum( line.original_amount or line.amount for line in rec.installment_line_ids)
            if abs(calculated_original_total - expected_total) > 0.01:
                raise ValidationError(_(
                    "Total mismatch.\n\n"
                    "Installments total: %.2f\n"
                    "Expected total: %.2f\n\n"
                    "Discount differences are ignored."
                ) % (calculated_original_total, expected_total))

    
    @api.onchange("contract_template_id")
    def _onchange_contract_template_id(self):
        if self.id and self.contract_template_id:
            self._copy_template_data()
        
    def create(self, vals):
        record = super().create(vals)
        if record.contract_template_id:
            record._copy_template_data()
            record.generated_html = record._render_contract_html()
        return record
    
    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {
            "partner_id",
            "selling_price",
            "state",
        }
        if trigger_fields.intersection(vals.keys()):
            for rec in self.filtered("contract_template_id"):
                rec._update_generated_html()
            
        if "contract_template_id" in vals:
            for rec in self.filtered("contract_template_id"):
                rec._copy_template_data()

        return res

    def action_rerender_contract(self):
        self.ensure_one()
        self._update_generated_html()
        return True

    def action_print_contract(self):
        self.ensure_one()
        self.action_generate_preview()
        return self.env.ref("kx_realestate.action_report_contract_preparation").report_action(self)
    def action_generate_preview(self):
        for rec in self:
            if not rec.contract_template_id:
                raise UserError(_("Please select a Contract Template."))
            rec.generated_html = rec._render_contract_html()
            # rec._update_generated_html()
        return True

    def _copy_template_data(self):
        self.ensure_one()
        self.article_ids.unlink()
        self.clause_ids.unlink()
        self.variable_ids.unlink()
        article_map = {}
        for article in self.contract_template_id.article_ids.sorted("sequence"):
            new_article = self.env["contract.maker.article"].create({
                "maker_id": self.id,
                "sequence": article.sequence,
                "name": article.name,
                "description": article.description,
                "active": article.active,
            })
            article_map[article.id] = new_article.id
        for clause in self.contract_template_id.clause_ids.sorted("sequence"):
            self.env["contract.maker.clause"].create({
                "maker_id": self.id,
                "article_id": article_map[clause.article_id.id],
                "sequence": clause.sequence,
                "name": clause.name,
                "body": clause.body,
                "mandatory": clause.mandatory,
                "active": clause.active,
            })
        for variable in self.contract_template_id.variable_ids:
            self.env["contract.maker.variable"].create({
                "maker_id": self.id,
                "name": variable.name,
                "code": variable.code,
                "sequence": variable.sequence,
                "description": variable.description,
                "active": variable.active,
                "required": variable.required,
                "model_id": variable.model_id.id,
                "field_id": variable.field_id.id,
                "example_value": variable.example_value,
            })

class ContractInstallmentMaker(models.Model):
    _name = "contract.maker.installment"
    _inherit = "loan.line.rs.own"

    maker_id = fields.Many2one(
        "contract.maker",
        string="Contract Maker",
        required=True,
        ondelete="cascade",
    )
    number = fields.Char(string='Number', required=True,)
    trigger_type = fields.Selection(
        [
            ('date', 'Date'),
            ('construction', 'Construction'),
        ],
        default='date',
        string='Trigger Type',
        required=True,
    )
    trigger_level = fields.Selection(
        [('building', 'Building'), ('floor', 'Floor'), ('unit', 'Unit')],
        string='Trigger Level',
        # required=True,
    )
    date = fields.Date(string='Due Date')
    trigger_building_type_id = fields.Many2one('building.type', compute='_compute_trigger_building_type_id')
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
    selected_floor_id = fields.Many2one('re.floor', string="Floor #", store=True)
    payment_term_date_id = fields.Many2one('payment.term.config', string='Payment Term Date')
    discount_percent = fields.Float(string='Discount (%)')
    amount = fields.Float(
        string='Payment',
        digits='Product Price',
    )

class HandoverChecklist(models.Model):
    _name = 'handover.checklist'
    _order = 'sequence, id'

    maker_id = fields.Many2one(
        "contract.maker",
        string="Contract Maker",
        # required=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one(
        "ownership.contract",
        # required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Checklist Item', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('handover', 'Handover'),
        ('cancel', 'Cancelled'),
        ('closed', 'Closed')
    ], default='draft', string="State")
    checklist_type = fields.Selection(
        [('common', 'Common'), ('individual', 'Individual')],
        default='common',
        required=True,
    )    
    done = fields.Boolean(default=False)
    is_fully_paid = fields.Boolean(
        related='contract_id.is_fully_paid',
        string='Fully Paid',
        store=True
    )
    checklist_date = fields.Date(string='Date', required=True)

class TermPenaltyRule(models.Model):
    _name = 'term.penalty.rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    maker_id = fields.Many2one(
        "contract.maker",
        string="Contract Maker",
        # required=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one(
        "ownership.contract",
        # required=True,
        ondelete="cascade",
    )
    name = fields.Char()

    sequence = fields.Integer(default=10)
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


    rule_met = fields.Boolean(string='Rule Met', compute='_compute_rule_met', store=True)
    trigger_hit = fields.Boolean(string='Trigger Hit', readonly=False)


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





class ContractMakerArticle(models.Model):
    _name = 'contract.maker.article'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    maker_id = fields.Many2one(
        "contract.maker",
        required=True,
        ondelete="cascade",
    )
    clause_ids = fields.One2many(
        "contract.maker.clause",
        "article_id",
        string="Clauses",
    )
    clause_count = fields.Integer(compute='_compute_clause_count', string='Clauses')

    @api.depends('clause_ids')
    def _compute_clause_count(self):
        for rec in self:
            rec.clause_count = len(rec.clause_ids)
        
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("maker_id")._update_generated_html()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.mapped("maker_id")._update_generated_html()
        return res

    def unlink(self):
        makers = self.mapped("maker_id")
        res = super().unlink()
        makers._update_generated_html()
        return res
    

class ContractMakerClause(models.Model):
    _name = 'contract.maker.clause'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Clause Title', required=True)
    body = fields.Html(string='Clause Body', sanitize=True, sanitize_attributes=False)
    mandatory = fields.Boolean(string='Mandatory', default=True)
    active = fields.Boolean(default=True)
    maker_id = fields.Many2one(
        "contract.maker",
        required=True,
        ondelete="cascade",
    )

    article_id = fields.Many2one(
        "contract.maker.article",
        required=True,
        ondelete="cascade",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("maker_id")._update_generated_html()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.mapped("maker_id")._update_generated_html()
        return res

    def unlink(self):
        makers = self.mapped("maker_id")
        res = super().unlink()
        makers._update_generated_html()
        return res


class ContractMakerVariable(models.Model):
    _name = "contract.maker.variable"
    _order = "sequence,id"

    name = fields.Char(required=True)

    code = fields.Char(required=True,help="Use inside clauses as {{Code}}",)
    sequence = fields.Integer(default=10)
    description = fields.Text()

    active = fields.Boolean(default=True)
    required = fields.Boolean(default=True)
    maker_id = fields.Many2one(
        "contract.maker",
        required=True,
        ondelete="cascade",
    )
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("maker_id")._update_generated_html()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.mapped("maker_id")._update_generated_html()
        return res

    def unlink(self):
        makers = self.mapped("maker_id")
        res = super().unlink()
        makers._update_generated_html()
        return res