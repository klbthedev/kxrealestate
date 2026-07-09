# -*- coding: utf-8 -*-
{
    'name': 'Contract Management',
    'version': '18.0.1.0.0',
    'category': 'Legal',
    'summary': 'Template-driven Contract Management System with live preview and e-signature workflow',
    'description': """
Contract Management System
===========================
Create reusable contract templates composed of Articles and Clauses with
dynamic Variables. Generate legal contracts from templates, fill in
variable values with an instant live preview, and drive contracts through
a Draft -> Review -> Approved -> Signed -> Archived workflow.

Key Features
------------
* Contract Templates with Articles, Clauses and Variables
* Variable replacement engine ({{VariableCode}} syntax)
* Live HTML preview via OWL component and RPC (no page refresh)
* QWeb PDF generation with header/footer/logo/page numbers
* Full approval workflow with chatter tracking
* Dashboard (graph/pivot) for contract statistics
* Customer portal access (view / download / track status)
* REST API controllers for templates and contracts
* Scheduled actions for expiry reminders and auto-archival
""",
    'author': 'kalab:kalab.work5@gmail.com',
    # 'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'portal'],
    'data': [
        # security
        'security/contract_management_security.xml',
        'security/ir.model.access.csv',
        'security/contract_record_rules.xml',
        # data
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        # views
        'views/contract_template_views.xml',
        'views/contract_article_views.xml',
        'views/contract_clause_views.xml',
        'views/contract_variable_views.xml',
        'views/contract_contract_views.xml',
        'views/contract_dashboard_views.xml',
        'views/portal_templates.xml',
        'views/contract_management_menus.xml',
        # report
        'report/contract_report.xml',
        'report/contract_report_templates.xml',
        # demo
    ],
    'demo': [
        'demo/contract_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'contract_management/static/src/js/contract_live_preview.js',
            'contract_management/static/src/xml/contract_live_preview.xml',
            'contract_management/static/src/css/contract_management.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
