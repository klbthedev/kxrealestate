# -*- coding: utf-8 -*-
import json

from odoo import http, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request


class ContractManagementAPI(http.Controller):
    """REST-style JSON API for the Contract Management module.

    All endpoints require an authenticated Odoo session (auth='user').
    Responses are plain JSON dicts; errors are returned with an 'error' key
    and an appropriate HTTP-like status embedded in the payload since the
    endpoints are exposed as type='json' (JSON-RPC over HTTP).
    """

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------
    @http.route('/api/contract/templates', type='json', auth='user', methods=['GET'], csrf=False)
    def get_templates(self, **kwargs):
        domain = [('state', '=', 'approved')]
        templates = request.env['contract.template'].search(domain)
        return {
            'count': len(templates),
            'templates': [self._template_to_dict(t) for t in templates],
        }

    @http.route('/api/contract/templates/<int:template_id>', type='json', auth='user', methods=['GET'], csrf=False)
    def get_template(self, template_id, **kwargs):
        template = request.env['contract.template'].browse(template_id).exists()
        if not template:
            return {'error': 'Template not found'}
        return self._template_to_dict(template, detailed=True)

    def _template_to_dict(self, template, detailed=False):
        data = {
            'id': template.id,
            'name': template.name,
            'code': template.code,
            'version': template.version,
            'state': template.state,
        }
        if detailed:
            data['articles'] = [{
                'id': a.id,
                'name': a.name,
                'clauses': [{
                    'id': c.id,
                    'name': c.name,
                    'mandatory': c.mandatory,
                } for c in a.clause_ids.filtered('active')],
            } for a in template.article_ids.filtered('active')]
            data['variables'] = [{
                'id': v.id,
                'name': v.name,
                'code': v.code,
                'data_type': v.data_type,
                'required': v.required,
                'default_value': v.default_value,
            } for v in template.variable_ids]
        return data

    # ------------------------------------------------------------------
    # Contracts
    # ------------------------------------------------------------------
    @http.route('/api/contract/contracts', type='json', auth='user', methods=['GET'], csrf=False)
    def get_contracts(self, **kwargs):
        domain = []
        if kwargs.get('partner_id'):
            domain.append(('partner_id', '=', int(kwargs['partner_id'])))
        if kwargs.get('state'):
            domain.append(('state', '=', kwargs['state']))
        contracts = request.env['contract.contract'].search(domain)
        return {
            'count': len(contracts),
            'contracts': [self._contract_to_dict(c) for c in contracts],
        }

    @http.route('/api/contract/contracts/<int:contract_id>', type='json', auth='user', methods=['GET'], csrf=False)
    def get_contract(self, contract_id, **kwargs):
        contract = request.env['contract.contract'].browse(contract_id).exists()
        if not contract:
            return {'error': 'Contract not found'}
        return self._contract_to_dict(contract, detailed=True)

    @http.route('/api/contract/contracts', type='json', auth='user', methods=['POST'], csrf=False)
    def create_contract(self, **kwargs):
        payload = kwargs
        required_fields = ('partner_id', 'template_id')
        missing = [f for f in required_fields if not payload.get(f)]
        if missing:
            return {'error': _('Missing required fields: %s') % ', '.join(missing)}
        try:
            vals = {
                'partner_id': int(payload['partner_id']),
                'template_id': int(payload['template_id']),
            }
            if payload.get('contract_date'):
                vals['contract_date'] = payload['contract_date']
            if payload.get('expiry_date'):
                vals['expiry_date'] = payload['expiry_date']
            contract = request.env['contract.contract'].create(vals)
            variable_values = payload.get('variable_values') or {}
            if variable_values:
                self._apply_variable_values(contract, variable_values)
            return self._contract_to_dict(contract, detailed=True)
        except (ValidationError, UserError) as exc:
            return {'error': str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {'error': _('Unexpected error: %s') % str(exc)}

    def _apply_variable_values(self, contract, variable_values):
        """variable_values: dict of {variable_code: raw_value}"""
        code_map = {line.variable_id.code: line for line in contract.variable_value_ids}
        for code, raw_value in variable_values.items():
            line = code_map.get(code)
            if line:
                line.set_value_from_raw(raw_value)

    def _contract_to_dict(self, contract, detailed=False):
        data = {
            'id': contract.id,
            'reference': contract.reference,
            'partner_id': contract.partner_id.id,
            'partner_name': contract.partner_id.name,
            'template_id': contract.template_id.id,
            'state': contract.state,
            'contract_date': contract.contract_date and contract.contract_date.isoformat(),
            'expiry_date': contract.expiry_date and contract.expiry_date.isoformat(),
        }
        if detailed:
            data['variable_values'] = {
                line.variable_id.code: line.get_display_value()
                for line in contract.variable_value_ids
            }
            data['generated_html'] = contract.generated_html
        return data

    # ------------------------------------------------------------------
    # Live preview RPC (used by the OWL component)
    # ------------------------------------------------------------------
    @http.route('/contract_management/live_preview', type='json', auth='user', csrf=False)
    def live_preview(self, contract_id, values=None, **kwargs):
        contract = request.env['contract.contract'].browse(int(contract_id)).exists()
        if not contract:
            return {'error': _('Contract not found')}
        try:
            html = contract.get_live_preview_html(override_values=values or {})
            return {'html': html}
        except Exception as exc:  # noqa: BLE001
            return {'error': str(exc)}
