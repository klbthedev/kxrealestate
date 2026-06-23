from odoo import api, fields, models, _
from odoo.addons.web_editor.tools import get_video_embed_code
from odoo.exceptions import ValidationError

class BuildingImages(models.Model):
    _name = 'building.images'
    _description = "Building Images"
    _inherit = ['image.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    building_id = fields.Many2one('building.building', string="Building", ondelete='cascade')
    can_image_1024_be_zoomed = fields.Boolean(string="Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed', store=True)
    embed_code = fields.Char(compute="_compute_embed_code")
    image = fields.Image(required=True)
    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10)
    video_url = fields.Char(string='Video URL', help='URL of a video for showcasing your property.')

    @api.depends('image', 'image_1024')
    def _compute_can_image_1024_be_zoomed(self):
        for image in self:
            # Odoo 18 no longer exposes tools.is_image_size_above.
            # Keep zoom enabled when source binary exists and differs from resized image.
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
