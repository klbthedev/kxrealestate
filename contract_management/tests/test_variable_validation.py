# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestVariableValidation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.template = self.env['contract.template'].create({
            'name': 'Validation Template',
            'code': 'VAL-01',
        })

    def test_invalid_code_format_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['contract.variable'].create({
                'template_id': self.template.id,
                'name': 'Bad Code',
                'code': '1invalid-code',
                'data_type': 'char',
            })

    def test_duplicate_code_per_template_rejected(self):
        self.env['contract.variable'].create({
            'template_id': self.template.id,
            'name': 'Var 1',
            'code': 'DupCode',
            'data_type': 'char',
        })
        with self.assertRaises(Exception):
            self.env['contract.variable'].create({
                'template_id': self.template.id,
                'name': 'Var 2',
                'code': 'DupCode',
                'data_type': 'char',
            })

    def test_invalid_regex_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['contract.variable'].create({
                'template_id': self.template.id,
                'name': 'Bad Regex',
                'code': 'BadRegex',
                'data_type': 'char',
                'validation_regex': '[unclosed(',
            })

    def test_many2one_requires_relation_model(self):
        with self.assertRaises(ValidationError):
            self.env['contract.variable'].create({
                'template_id': self.template.id,
                'name': 'Generic Rel',
                'code': 'GenericRel',
                'data_type': 'many2one',
            })

    def test_regex_validation_applied_on_value(self):
        variable = self.env['contract.variable'].create({
            'template_id': self.template.id,
            'name': 'Zip Code',
            'code': 'ZipCode',
            'data_type': 'char',
            'validation_regex': r'^\d{5}$',
        })
        with self.assertRaises(ValidationError):
            variable.validate_value('ABCDE')
        # should not raise
        variable.validate_value('12345')

    def test_required_variable_rejects_empty(self):
        variable = self.env['contract.variable'].create({
            'template_id': self.template.id,
            'name': 'Mandatory Field',
            'code': 'MandatoryField',
            'data_type': 'char',
            'required': True,
        })
        with self.assertRaises(ValidationError):
            variable.validate_value('')
