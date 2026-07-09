# -*- coding: utf-8 -*-
import base64

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ContractCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'contract_count' in counters:
            values['contract_count'] = request.env['contract.contract'].search_count(
                self._get_contract_domain())
        return values

    def _get_contract_domain(self):
        return [('partner_id', '=', request.env.user.partner_id.id)]

    @http.route(['/my/contracts', '/my/contracts/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_contracts(self, page=1, sortby=None, **kwargs):
        Contract = request.env['contract.contract']
        domain = self._get_contract_domain()

        searchbar_sortings = {
            'date': {'label': _('Contract Date'), 'order': 'contract_date desc'},
            'reference': {'label': _('Reference'), 'order': 'reference'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        sortby = sortby or 'date'
        order = searchbar_sortings[sortby]['order']

        contract_count = Contract.search_count(domain)
        pager = portal_pager(
            url='/my/contracts', total=contract_count, page=page, step=self._items_per_page)
        contracts = Contract.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values = {
            'contracts': contracts,
            'page_name': 'contract',
            'pager': pager,
            'default_url': '/my/contracts',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        }
        return request.render('contract_management.portal_my_contracts', values)

    @http.route(['/my/contracts/<int:contract_id>'], type='http', auth='user', website=True)
    def portal_contract_detail(self, contract_id, **kwargs):
        try:
            contract_sudo = self._document_check_access('contract.contract', contract_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = {
            'contract': contract_sudo,
            'page_name': 'contract',
        }
        return request.render('contract_management.portal_contract_page', values)

    @http.route(['/my/contracts/<int:contract_id>/pdf'], type='http', auth='user', website=True)
    def portal_contract_pdf(self, contract_id, **kwargs):
        try:
            contract_sudo = self._document_check_access('contract.contract', contract_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if not contract_sudo.generated_pdf:
            return request.redirect('/my/contracts/%s' % contract_id)
        pdf_content = base64.b64decode(contract_sudo.generated_pdf)
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'attachment; filename="%s"' % (
                contract_sudo.generated_pdf_name or 'contract.pdf')),
        ]
        return request.make_response(pdf_content, headers=headers)
