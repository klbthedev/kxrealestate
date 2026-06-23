from odoo import fields, models

class unit_attachment_line(models.Model):
    _name = 'unit.attachment.line'

    file = fields.Binary(string='File', required=True)
    name = fields.Char(string='Description', required=True)
    product_attach_id = fields.Many2one('product.template', string='Linked Property', ondelete='cascade', readonly=True)

    def download_file(self):
        self.env.cr.execute("select id from ir_attachment where res_model='"+str(self._name)+"' and res_id="+str(self.id))
        attachment_id = self.env.cr.fetchone()[0] or None
        if attachment_id:
            attachment = self.env['ir.attachment'].sudo().browse(attachment_id)
            if attachment:
                action = {
                    'type': 'ir.actions.act_url',
                    'url': "web/content/?model=ir.attachment&id=" + str(attachment.id) + "&filename_field=name&field=datas&download=true&name=" + str(attachment.store_fname),
                    'target': 'self'
                }
                return action
