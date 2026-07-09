# -*- coding: utf-8 -*-
"""Reusable variable-replacement service for Contract Management.

Exposed as an Odoo abstract model (``contract.template.renderer``) so it can
be called both from ORM code (``self.env['contract.template.renderer']``)
and easily unit-tested / reused from controllers and OWL RPC endpoints.

Variable syntax supported inside template / clause HTML::

    {{VariableCode}}

Unknown placeholders are left untouched in the output so authors can spot
typos, and any raw text used for replacement is HTML-escaped to avoid
markup injection while still allowing the surrounding clause HTML to
render normally.
"""
import logging
import re
from markupsafe import Markup, escape

from odoo import models

_logger = logging.getLogger(__name__)

# Matches {{Code}}, tolerant of surrounding whitespace: {{ Code }}
VARIABLE_PATTERN = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}')


class ContractTemplateRenderer(models.AbstractModel):
    _name = 'contract.template.renderer'
    _description = 'Contract Template Variable Renderer Service'

    def render(self, template_html, values):
        """Replace every {{Code}} placeholder found in ``template_html`` with
        the corresponding entry from ``values`` (dict of code -> string).

        :param str template_html: raw HTML containing placeholders.
        :param dict values: mapping of variable code -> replacement text.
        :return: str rendered HTML, safe to store/display.
        """
        if not template_html:
            return ''
        values = values or {}

        def _replace(match):
            code = match.group(1)
            if code in values and values[code] not in (None, False):
                return str(escape(str(values[code])))
            # Leave unresolved placeholders visible so users notice missing data
            return match.group(0)

        try:
            rendered = VARIABLE_PATTERN.sub(_replace, template_html)
        except Exception:
            _logger.exception('Contract template rendering failed, returning source HTML unchanged.')
            return template_html
        return rendered

    def extract_variable_codes(self, template_html):
        """Return the sorted list of unique variable codes referenced inside
        the given HTML, useful to detect unused/undeclared variables."""
        if not template_html:
            return []
        return sorted(set(VARIABLE_PATTERN.findall(template_html)))
