from odoo import api, fields, models, _
from odoo.addons.web_editor.tools import get_video_embed_code
from odoo.exceptions import ValidationError

class PropertyImage(models.Model):
    _name = 'property.image'
    _description = "Product Image"
    _inherit = ['image.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    can_image_1024_be_zoomed = fields.Boolean(string="Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed', store=True)
    embed_code = fields.Char(compute="_compute_embed_code")
    image = fields.Image(required=True)
    name = fields.Char("Name", required=True)
    product_tmplate_id = fields.Many2one('product.template', string="Product Template", ondelete='cascade')
    product_variant_id = fields.Many2one('product.product', string="Product Variant", ondelete='cascade')
    sequence = fields.Integer(default=10)
    video_url = fields.Char(string='Video URL', help='URL of a video for showcasing your product.')

    @api.depends('image', 'image_1024')
    def _compute_can_image_1024_be_zoomed(self):
        for image in self:
            image.can_image_1024_be_zoomed = bool(image.image and image.image_1024 and image.image != image.image_1024)

    @api.depends('video_url')
    def _compute_embed_code(self):
        for image in self:
            image.embed_code = get_video_embed_code(image.video_url)

    @api.constrains('video_url')
    def _check_valid_video_url(self):
        for image in self:
            if image.video_url and not image.embed_code:
                raise ValidationError(_("Provided video URL for '%s' is not valid. Please enter a valid video URL.", image.name))

    @api.model_create_multi
    def create(self, vals_list):
        context_without_template = self.with_context({k: v for k, v in self.env.context.items() if k != 'default_product_tmpl_id'})
        normal_vals = []
        variant_vals_list = []

        for vals in vals_list:
            if vals.get('product_variant_id') and 'default_product_tmpl_id' in self.env.context:
                variant_vals_list.append(vals)
            else:
                normal_vals.append(vals)
        return super().create(normal_vals) + super(PropertyImage, context_without_template).create(variant_vals_list)
