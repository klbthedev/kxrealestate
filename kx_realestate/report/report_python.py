from odoo import models

class PropertyStatusPdfReport(models.AbstractModel):
    _name = 'report.kx_realestate.property_status_pdf_template'
    _description = 'Property Status PDF Report'

    def _get_report_values(self, docids, data=None):

        Property = self.env['product.template']
        base_domain = [('is_property', '=', True)]

        free_count = Property.search_count(base_domain + [('state', '=', 'free')])
        sold_count = Property.search_count(base_domain + [('state', '=', 'sold')])
        blocked_count = Property.search_count(base_domain + [('state', '=', 'blocked')])
        total_properties = (free_count + sold_count + blocked_count)

        report_lines = [
            {'status': 'Free', 'count': free_count,},
            {'status': 'Sold', 'count': sold_count,},
            {'status': 'Blocked', 'count': blocked_count,},
        ]

        return {
            'doc_ids': docids,
            'doc_model': 'property.status.report.wizard',
            'docs': self.env['property.status.report.wizard'].browse(docids),
            'report_lines': report_lines,
            'total_properties': total_properties,
        }