# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
            'contract_management.action_contract_contract')
        action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def action_view_articles(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'contract_management.action_contract_article')
        action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def action_view_variables(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'contract_management.action_contract_variable')
        action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def get_combined_html(self):
        """Build the raw (unreplaced) HTML body for this template, concatenating
        every active Article and its active Clauses in sequence order.
        Used as the source that the template_renderer service replaces
        variables into.
        """
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
