from odoo import fields, models

class SiteRegion(models.Model):
    _name = "site.region"
    _description = "Region Name"
    
    #####################################################
    
    name = fields.Char(String="Region Name", required=True)
    city_id = fields.One2many("site.city", "region_id", string="City Name", )

    _sql_constraints = [
        (
            "region_unique",
            "unique(name)",
            "A region with the same name already exists.",
        ),
    ]

    ####################################################