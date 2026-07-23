from odoo import fields, models

class SiteCity(models.Model):
    _name = "site.city"
    _description = "City Name"
    
    #############################################################
    
    name = fields.Char(String="City Name", required=True)
    region_id = fields.Many2one("site.region", string="Region Name", required=True, ondelete="cascade",)
    site_id = fields.One2many("re.site", "city_id", string="Site Name",)
    
    _sql_constraints = [
        (
            "city_unique",
            "unique(name,region_id)",
            "A city with the same name already exists in this region.",
        ),
    ]

    #############################################################