# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .contract_variable import RELATIONAL_TYPES


class ContractVariableValue(models.Model):
    _name = 'contract.variable.value'
    _description = 'Contract Variable Value'
    _order = 'sequence, id'
    _rec_name = 'variable_id'

    contract_id = fields.Many2one(
        'contract.contract', string='Contract', ondelete='cascade', required=True, index=True)
    variable_id = fields.Many2one(
        'contract.variable', string='Variable', required=True, ondelete='restrict')
    sequence = fields.Integer(related='variable_id.sequence', store=True)
    data_type = fields.Selection(related='variable_id.data_type', string='Data Type', readonly=True)
    required = fields.Boolean(related='variable_id.required', readonly=True)

    value_char = fields.Char(string='Text Value')
    value_text = fields.Text(string='Long Text Value')
    value_integer = fields.Integer(string='Integer Value')
    value_float = fields.Float(string='Float Value')
    value_date = fields.Date(string='Date Value')
    value_datetime = fields.Datetime(string='Datetime Value')
    value_boolean = fields.Boolean(string='Boolean Value')
    value_many2one_id = fields.Integer(string='Related Record ID')
    value_many2one_model = fields.Char(string='Related Model')
    value_many2one_name = fields.Char(
        string='Related Record Display Name', compute='_compute_value_many2one_name')

    _sql_constraints = [
        ('variable_contract_uniq', 'unique(variable_id, contract_id)',
         'A variable can only have one value per contract.'),
    ]

    @api.depends('value_many2one_id', 'value_many2one_model')
    def _compute_value_many2one_name(self):
        for rec in self:
            name = False
            if rec.value_many2one_model and rec.value_many2one_id:
                model = rec.env.get(rec.value_many2one_model)
                if model is not None:
                    record = model.browse(rec.value_many2one_id).exists()
                    if record:
                        name = record.display_name
            rec.value_many2one_name = name

    def get_display_value(self):
        """Return the human-readable replacement text for {{Code}} substitution."""
        self.ensure_one()
        dt = self.data_type
        if dt == 'char':
            return self.value_char or ''
        if dt == 'integer':
            return str(self.value_integer) if self.value_integer else '0'
        if dt == 'float':
            return ('%g' % self.value_float) if self.value_float else '0'
        if dt == 'date':
            return fields.Date.to_string(self.value_date) if self.value_date else ''
        if dt == 'datetime':
            return fields.Datetime.to_string(self.value_datetime) if self.value_datetime else ''
        if dt == 'boolean':
            return _('Yes') if self.value_boolean else _('No')
        if dt == 'selection':
            return self.value_char or ''
        if dt in RELATIONAL_TYPES:
            return self.value_many2one_name or ''
        return self.value_char or ''

    def set_value_from_raw(self, raw_value):
        """Store a raw value (as received from the frontend / API) into the
        correct typed column(s) according to the variable's data_type.
        """
        self.ensure_one()
        variable = self.variable_id
        variable.validate_value(raw_value)
        dt = variable.data_type
        vals = {
            'value_char': False, 'value_text': False, 'value_integer': 0,
            'value_float': 0.0, 'value_date': False, 'value_datetime': False,
            'value_boolean': False, 'value_many2one_id': False,
            'value_many2one_model': False,
        }
        if raw_value in (None, ''):
            self.write(vals)
            return
        if dt == 'char' or dt == 'selection':
            vals['value_char'] = raw_value
        elif dt == 'integer':
            vals['value_integer'] = int(raw_value)
        elif dt == 'float':
            vals['value_float'] = float(raw_value)
        elif dt == 'date':
            vals['value_date'] = raw_value
        elif dt == 'datetime':
            vals['value_datetime'] = raw_value
        elif dt == 'boolean':
            vals['value_boolean'] = bool(raw_value) if not isinstance(raw_value, str) \
                else raw_value.lower() in ('1', 'true', 'yes', 'on')
        elif dt in RELATIONAL_TYPES:
            model_name = variable.get_relation_model_name()
            if not model_name:
                raise ValidationError(_('No target model configured for variable "%s".') % variable.name)
            vals['value_many2one_id'] = int(raw_value)
            vals['value_many2one_model'] = model_name
        self.write(vals)
