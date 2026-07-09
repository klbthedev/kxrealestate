# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

DATA_TYPE_SELECTION = [
    ('char', 'Text'),
    ('integer', 'Integer'),
    ('float', 'Float'),
    ('date', 'Date'),
    ('datetime', 'Datetime'),
    ('boolean', 'Boolean'),
    ('selection', 'Selection'),
    ('partner', 'Partner (Contact)'),
    ('company', 'Company'),
    ('employee', 'Employee'),
    ('user', 'User'),
    ('many2one', 'Many2one (Generic Model)'),
]

# data types that are stored as a relational (integer id) value
RELATIONAL_TYPES = ('partner', 'company', 'employee', 'user', 'many2one')

# mapping from data type to the target model used for relational variables
RELATIONAL_MODEL_MAP = {
    'partner': 'res.partner',
    'company': 'res.company',
    'employee': 'hr.employee',
    'user': 'res.users',
}


class ContractVariable(models.Model):
    _name = 'contract.variable'
    _description = 'Contract Template Variable'
    _order = 'sequence, id'

    name = fields.Char(string='Variable Name', required=True)
    code = fields.Char(
        string='Variable Code', required=True,
        help='Code used inside clause bodies as {{Code}} for replacement.')
    sequence = fields.Integer(string='Sequence', default=10)
    example_value = fields.Char(string='Example Value')
    description = fields.Text(string='Description')
    data_type = fields.Selection(
        DATA_TYPE_SELECTION, string='Data Type', required=True, default='char')
    selection_options = fields.Text(
        string='Selection Options',
        help='For Selection type: one "key:Label" pair per line.')
    relation_model_id = fields.Many2one(
        'ir.model', string='Related Model',
        help='Target model for a generic Many2one variable type.',
        domain=[('transient', '=', False)])
    required = fields.Boolean(string='Required', default=True)
    default_value = fields.Char(string='Default Value')
    validation_regex = fields.Char(
        string='Validation Regex',
        help='Optional regular expression the entered value must match '
             '(applies to Text type variables).')
    active = fields.Boolean(default=True)
    template_id = fields.Many2one(
        'contract.template', string='Template', ondelete='cascade', index=True)
    company_id = fields.Many2one(
        related='template_id.company_id', store=True, string='Company', readonly=True)

    _sql_constraints = [
        ('code_template_uniq', 'unique(code, template_id)',
         'Variable code must be unique per template.'),
    ]

    @api.constrains('code')
    def _check_code_format(self):
        code_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
        for rec in self:
            if rec.code and not code_re.match(rec.code):
                raise ValidationError(_(
                    'Variable code "%s" is invalid. Codes must start with a '
                    'letter or underscore and contain only letters, digits '
                    'and underscores (used as {{%s}}).') % (rec.code, rec.code))

    @api.constrains('validation_regex')
    def _check_regex_valid(self):
        for rec in self:
            if rec.validation_regex:
                try:
                    re.compile(rec.validation_regex)
                except re.error as exc:
                    raise ValidationError(_(
                        'Validation Regex for variable "%s" is not a valid '
                        'regular expression: %s') % (rec.name, exc))

    @api.constrains('data_type', 'relation_model_id')
    def _check_many2one_model(self):
        for rec in self:
            if rec.data_type == 'many2one' and not rec.relation_model_id:
                raise ValidationError(_(
                    'Please select a Related Model for the Many2one variable "%s".'
                ) % rec.name)

    def get_relation_model_name(self):
        """Return the technical model name a relational value should be stored against."""
        self.ensure_one()
        if self.data_type in RELATIONAL_MODEL_MAP:
            return RELATIONAL_MODEL_MAP[self.data_type]
        if self.data_type == 'many2one' and self.relation_model_id:
            return self.relation_model_id.model
        return False

    def validate_value(self, raw_value):
        """Validate a raw (string) value entered by the user for this variable.
        Raises ValidationError if invalid. Returns nothing.
        """
        self.ensure_one()
        if self.required and (raw_value is None or raw_value == ''):
            raise ValidationError(_('Variable "%s" is required.') % self.name)
        if raw_value in (None, '') :
            return
        if self.data_type == 'integer':
            try:
                int(raw_value)
            except (ValueError, TypeError):
                raise ValidationError(_('Variable "%s" must be an integer.') % self.name)
        elif self.data_type == 'float':
            try:
                float(raw_value)
            except (ValueError, TypeError):
                raise ValidationError(_('Variable "%s" must be a number.') % self.name)
        elif self.data_type == 'char' and self.validation_regex:
            if not re.match(self.validation_regex, str(raw_value)):
                raise ValidationError(_(
                    'Value for "%s" does not match the required format.') % self.name)
