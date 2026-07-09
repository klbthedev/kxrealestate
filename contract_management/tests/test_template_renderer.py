# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTemplateRenderer(TransactionCase):

    def setUp(self):
        super().setUp()
        self.renderer = self.env['contract.template.renderer']

    def test_simple_replacement(self):
        html = '<p>Hello {{PartnerName}}, today is {{Today}}.</p>'
        values = {'PartnerName': 'Acme Corp', 'Today': '2026-07-09'}
        rendered = self.renderer.render(html, values)
        self.assertEqual(rendered, '<p>Hello Acme Corp, today is 2026-07-09.</p>')

    def test_whitespace_tolerant_placeholder(self):
        html = '<p>{{  PartnerName }} vs {{PartnerName}}</p>'
        values = {'PartnerName': 'Acme'}
        rendered = self.renderer.render(html, values)
        self.assertEqual(rendered, '<p>Acme vs Acme</p>')

    def test_unresolved_placeholder_kept(self):
        html = '<p>{{UnknownVar}}</p>'
        rendered = self.renderer.render(html, {})
        self.assertIn('{{UnknownVar}}', rendered)

    def test_html_escaping(self):
        html = '<p>{{Name}}</p>'
        values = {'Name': '<script>alert(1)</script>'}
        rendered = self.renderer.render(html, values)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_extract_variable_codes(self):
        html = '<p>{{A}} and {{B}} and {{A}}</p>'
        codes = self.renderer.extract_variable_codes(html)
        self.assertEqual(codes, ['A', 'B'])

    def test_empty_template(self):
        self.assertEqual(self.renderer.render('', {'X': 'Y'}), '')
        self.assertEqual(self.renderer.render(False, {'X': 'Y'}), '')
