# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccessRights(TransactionCase):

    def setUp(self):
        super().setUp()
        self.legal_user_group = self.env.ref('contract_management.group_contract_legal_user')
        self.legal_manager_group = self.env.ref('contract_management.group_contract_legal_manager')

        self.legal_user = self.env['res.users'].create({
            'name': 'Legal User',
            'login': 'legal_user_test',
            'email': 'legal_user_test@example.com',
            'groups_id': [(6, 0, [self.legal_user_group.id, self.env.ref('base.group_user').id])],
        })
        self.legal_manager = self.env['res.users'].create({
            'name': 'Legal Manager',
            'login': 'legal_manager_test',
            'email': 'legal_manager_test@example.com',
            'groups_id': [(6, 0, [self.legal_manager_group.id, self.env.ref('base.group_user').id])],
        })

        self.template = self.env['contract.template'].create({
            'name': 'Access Test Template',
            'code': 'ACC-01',
        })
        self.env['contract.article'].create({
            'template_id': self.template.id,
            'name': 'Article 1',
        })
        self.template.action_approve()

        self.partner = self.env['res.partner'].create({'name': 'Access Test Customer'})

    def test_legal_user_cannot_create_template(self):
        with self.assertRaises(AccessError):
            self.env['contract.template'].with_user(self.legal_user).create({
                'name': 'Should Fail',
                'code': 'FAIL-01',
            })

    def test_legal_manager_can_create_template(self):
        template = self.env['contract.template'].with_user(self.legal_manager).create({
            'name': 'Manager Template',
            'code': 'MGR-01',
        })
        self.assertTrue(template)

    def test_legal_user_can_create_contract(self):
        contract = self.env['contract.contract'].with_user(self.legal_user).create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
        })
        self.assertTrue(contract)

    def test_legal_user_only_sees_own_contracts(self):
        contract_a = self.env['contract.contract'].with_user(self.legal_manager).create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
            'user_id': self.legal_manager.id,
        })
        contract_b = self.env['contract.contract'].with_user(self.legal_user).create({
            'partner_id': self.partner.id,
            'template_id': self.template.id,
            'user_id': self.legal_user.id,
        })
        visible = self.env['contract.contract'].with_user(self.legal_user).search([])
        self.assertIn(contract_b.id, visible.ids)
        self.assertNotIn(contract_a.id, visible.ids)
