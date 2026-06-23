from odoo import fields, models

class BuildingAttachmentLine(models.Model):
    _name = 'building.attachment.line'

    name = fields.Char(string='Name', required=True)
    file = fields.Binary(string='File', required=True)
    building_id = fields.Many2one('building.building', ondelete='cascade', readonly=True)

    def download_file(self):
        self.env.cr.execute("select id from ir_attachment where res_model='"+str(self._name)+"' and res_id="+str(self.id))
        attachment_id= self.env.cr.fetchone()[0] or None
        if attachment_id:
            attachment = self.env['ir.attachment'].sudo().browse(attachment_id)
            if attachment:
                action = {
                    'type': 'ir.actions.act_url',
                    'url': "web/content/?model=ir.attachment&id=" + str(attachment.id) + "&filename_field=name&field=datas&download=true&name=" + str(attachment.store_fname),
                    'target': 'self'
                }
                return action
