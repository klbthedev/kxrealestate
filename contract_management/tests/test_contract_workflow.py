# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContractWorkflow(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Customer'})
        self.template = self.env['contract.template'].create({
            'name': 'Test Template',
            'code': 'TT-01',
        })
        self.article = self.env['contract.article'].create({
            'template_id': self.template.id,
            'name': 'Article 1',
        })
        self.env['contract.clause'].create({
            'article_id': self.article.id,
            'name': 'Clause 1',
            'body': '<p>Hello {{PartnerName}}, amount due {{Amount}}.</p>',
        })
        self.variable = self.env['contract.variable'].create({
            'template_id': self.template.id,
            'name': 'Amount',
            'code': 'Amount',
            'data_type': 'float',
            'required': True,
        })

    def test_template_approve_requires_articles(self):
        empty_template = self.env['contract.template'].create({
            'name': 'Empty',
            'code': 'EMPTY-01',
        })
        with self.assertRaises(UserError):
            empty_template.action_approve()

    def test_template_approve_ok(self):
        self.template.action_approve()
        self.assertEqual(self.template.state, 'approved')

    def test_contract_reference_sequence(self):
        self.template.action_approve()
        contract = self.env['contract.contract'].create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
        })
        self.assertNotEqual(contract.reference, 'New')
        self.assertTrue(contract.reference.startswith('CTR/'))

    def test_variable_values_synced_on_create(self):
        self.template.action_approve()
        contract = self.env['contract.contract'].create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
        })
        self.assertEqual(len(contract.variable_value_ids), 1)
        self.assertEqual(contract.variable_value_ids.variable_id, self.variable)

    def test_submit_review_blocks_missing_required_variable(self):
        self.template.action_approve()
        contract = self.env['contract.contract'].create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
        })
        with self.assertRaises(ValidationError):
            contract.action_submit_review()

    def test_full_workflow(self):
        self.template.action_approve()
        contract = self.env['contract.contract'].create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
        })
        contract.variable_value_ids.set_value_from_raw(42.5)
        contract.action_submit_review()
        self.assertEqual(contract.state, 'review')
        contract.action_approve()
        self.assertEqual(contract.state, 'approved')
        contract.action_sign()
        self.assertEqual(contract.state, 'signed')
        self.assertTrue(contract.generated_pdf)
        self.assertIn('Test Customer', contract.generated_html)
        self.assertIn('42.5', contract.generated_html)

    def test_signed_contract_cannot_be_cancelled(self):
        self.template.action_approve()
        contract = self.env['contract.contract'].create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
        })
        contract.variable_value_ids.set_value_from_raw(10)
        contract.action_submit_review()
        contract.action_approve()
        contract.action_sign()
        with self.assertRaises(UserError):
            contract.action_cancel()
