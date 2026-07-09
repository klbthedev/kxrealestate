# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
        'contract.article', string='Article', ondelete='cascade', required=True, index=True)
    template_id = fields.Many2one(
        related='article_id.template_id', string='Template', store=True, readonly=True)
    company_id = fields.Many2one(
        related='article_id.company_id', store=True, string='Company', readonly=True)
