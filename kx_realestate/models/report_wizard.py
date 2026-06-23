from odoo import models

class PropertyStatusReportWizard(models.TransientModel):
    _name = 'property.status.report.wizard'
    _description = 'Property Status Report Wizard'

    def action_print_report(self):

        return self.env.ref(
            'kx_realestate.action_property_status_pdf_report'
        ).report_action(self)