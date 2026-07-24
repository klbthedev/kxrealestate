from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class LandAcquisitionStage(models.Model):
    _name = "land.acquisition.stage"
    _description = "Land Acquisition Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="If enabled, this stage will be folded in Kanban.",
    )
    color = fields.Integer()
    probability = fields.Float(default=0.0)
    description = fields.Text()


class LandAcquisition(models.Model):
    _name = "land.acquisition"
    _description = "Land Acquisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = sequence.next_by_code("land.acquisition") or _("New")

            if not vals.get("stage_id"):
                stage = self.env["land.acquisition.stage"].search(
                    [("active", "=", True)],
                    order="sequence",
                    limit=1,
                )
                if stage:
                    vals["stage_id"] = stage.id

        return super().create(vals_list)

    # Identification

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        readonly=True,
        tracking=True,
    )

    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    stage_id = fields.Many2one(
        "land.acquisition.stage",
        string="Stage",
        tracking=True,
        group_expand="_read_group_stage_ids",
        ondelete="restrict",
    )

    # General Information

    land_name = fields.Char(
        string="Land Name",
        tracking=True,
    )

    owner_id = fields.Many2one(
        "res.partner",
        string="Current Owner",
        tracking=True,
    )

    owner_phone = fields.Char(
        related="owner_id.phone",
        readonly=True,
    )

    owner_mobile = fields.Char(
        related="owner_id.mobile",
        readonly=True,
    )

    owner_email = fields.Char(
        related="owner_id.email",
        readonly=True,
    )

    # Location

    country_id = fields.Many2one(
        "res.country",
        string="Country",
    )

    state_id = fields.Many2one(
        "res.country.state",
        string="State / Region",
        domain="[('country_id', '=', country_id)]",
    )

    city = fields.Char()

    address = fields.Char()

    gps_latitude = fields.Float(
        digits=(9, 6),
    )

    gps_longitude = fields.Float(
        digits=(9, 6),
    )

    # Legal

    parcel_id = fields.Char(
        string="Parcel / Plot ID",
    )

    title_deed_no = fields.Char(
        string="Title Deed No.",
    )

    title_deed_date = fields.Date(
        string="Title Deed Date",
    )

    land_title_ref = fields.Char(
        string="Land Title Reference",
    )

    # Commercial

    land_area = fields.Float(
        string="Land Area (m²)",
    )

    expected_purchase_price = fields.Monetary(
        string="Expected Purchase Price",
        currency_field="currency_id",
        tracking=True,
    )

    negotiated_price = fields.Monetary(
        string="Negotiated Price",
        currency_field="currency_id",
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    expected_closing_date = fields.Date()

    note = fields.Html()

    document_ids = fields.One2many(
        "land.acquisition.document",
        "acquisition_id",
        string="Documents",
    )

    document_count = fields.Integer(
        string="Documents",
        compute="_compute_document_count",
    )

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env["land.acquisition.stage"].search([])

    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_ids)

    def action_view_documents(self):

        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Documents",
            "res_model": "land.acquisition.document",
            "view_mode": "tree,form",
            "domain": [
                (
                    "acquisition_id",
                    "=",
                    self.id,
                )
            ],
            "context": {
                "default_acquisition_id": self.id,
            },
        }

    converted = fields.Boolean(
        string="Converted",
        default=False,
        tracking=True,
    )

    converted_model = fields.Selection(
        [
            ("re.site", "Site"),
            ("building.building", "Building"),
        ],
        string="Converted Into",
        readonly=True,
        tracking=True,
    )

    converted_record_id = fields.Integer(
        string="Converted Record ID",
        readonly=True,
    )

    converted_date = fields.Datetime(
        readonly=True,
    )

    site_id = fields.Many2one(
        "re.site",
        string="Created Site",
        readonly=True,
    )

    building_id = fields.Many2one(
        "building.building",
        string="Created Building",
        readonly=True,
    )

    def _prepare_site_vals(self):
        self.ensure_one()

        return {
            "name": self.land_name or self.name,
            "company_id": self.company_id.id,
            "address": self.address,
        }

    def _prepare_building_vals(self):
        self.ensure_one()

        return {
            "name": self.land_name or self.name,
            "company_id": self.company_id.id,
            "address": self.address,
            "country_id": self.country_id.id,
            "state_id": self.state_id.id,
            "city": self.city,
            "gps_latitude": self.gps_latitude,
            "gps_longitude": self.gps_longitude,
            "gross_area": self.land_area,
            "land_title_ref": self.land_title_ref,
            "parcel_id": self.parcel_id,
            "title_deed_no": self.title_deed_no,
            "title_deed_date": self.title_deed_date,
        }

    def _check_conversion(self):
        self.ensure_one()
        if self.converted:
            raise UserError(_("This acquisition has already been converted."))
        if self.stage_id.name != "Acquired":
            raise UserError(_("Only acquired land can be converted."))

    def action_convert_to_site(self):
        self.ensure_one()
        self._check_conversion()
        site = self.env["re.site"].create(self._prepare_site_vals())
        self.write(
            {
                "converted": True,
                "converted_model": "re.site",
                "converted_record_id": site.id,
                "converted_date": fields.Datetime.now(),
                "site_id": site.id,
            }
        )
        self.message_post(body=_("Converted into Site: %s") % site.display_name)
        return {
            "type": "ir.actions.act_window",
            "name": _("Site"),
            "res_model": "re.site",
            "view_mode": "form",
            "res_id": site.id,
        }
    def action_convert_to_building(self):
        self.ensure_one()
        self._check_conversion()
        building = self.env["building.building"].create(self._prepare_building_vals())
        self.write(
            {
                "converted": True,
                "converted_model": "building.building",
                "converted_record_id": building.id,
                "converted_date": fields.Datetime.now(),
                "building_id": building.id,
            }
        )
        self.message_post(body=_("Converted into Building: %s") % building.display_name)
        return {
            "type": "ir.actions.act_window",
            "name": _("Building"),
            "res_model": "building.building",
            "view_mode": "form",
            "res_id": building.id,
        }

    def _prepare_site_vals(self):
        self.ensure_one()

        return {
            "name": self.land_name or self.name,
            "company_id": self.company_id.id,
            "address": self.address,
            "acquisition_id": self.id,
        }

    def _prepare_building_vals(self):
        self.ensure_one()

        return {
            "land_acquisition_name": self.land_name or self.name,
            "company_id": self.company_id.id,
            "address": self.address,
            "country_id": self.country_id.id,
            "state_id": self.state_id.id,
            "city": self.city,
            "gps_latitude": self.gps_latitude,
            "gps_longitude": self.gps_longitude,
            "gross_area": self.land_area,
            "land_title_ref": self.land_title_ref,
            "parcel_id": self.parcel_id,
            "title_deed_no": self.title_deed_no,
            "title_deed_date": self.title_deed_date,
            "acquisition_id": self.id,
        }


class LandAcquisitionDocument(models.Model):
    _name = "land.acquisition.document"
    _description = "Land Acquisition Document"

    name = fields.Char(
        string="Document Name",
        required=True,
    )

    acquisition_id = fields.Many2one(
        "land.acquisition",
        string="Land Acquisition",
        required=True,
        ondelete="cascade",
    )

    document_type = fields.Selection(
        [
            ("title", "Title Deed"),
            ("contract", "Contract"),
            ("legal", "Legal Document"),
            ("valuation", "Valuation"),
            ("other", "Other"),
        ],
        default="other",
        string="Document Type",
    )

    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Attachment",
        ondelete="set null",
    )

    notes = fields.Text()

    date = fields.Date(
        default=fields.Date.context_today,
    )
