# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ContractArticle(models.Model):
    _name = 'contract.article'
    _description = 'Contract Template Article'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    template_id = fields.Many2one(
        'contract.template', string='Template', ondelete='cascade', required=True, index=True)
    clause_ids = fields.One2many(
        'contract.clause', 'article_id', string='Clauses')
    clause_count = fields.Integer(compute='_compute_clause_count', string='Clauses')
    company_id = fields.Many2one(
        related='template_id.company_id', store=True, string='Company', readonly=True)

    @api.depends('clause_ids')
    def _compute_clause_count(self):
        for rec in self:
            rec.clause_count = len(rec.clause_ids)
