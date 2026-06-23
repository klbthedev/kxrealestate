from odoo import api, fields, models, _

class RealEstateSite(models.Model):
    _name = "re.site"
    _description = "Real Estate Site"
    _inherit = ['mail.thread']
    _order = 'sequence, name'
    ####################################################################
    active = fields.Boolean(default=True)
    block_ids = fields.One2many('re.block', 'site_id', string='Blocks')
    building_ids = fields.One2many('building.building', 'site_id', string='Buildings')
    code = fields.Char(string='Code', tracking=True, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    name = fields.Char(required=True, tracking=True)
    ####################################################################
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == '/':
                vals['code'] = self.env['ir.sequence'].next_by_code('re.site') or '/'
        return super().create(vals_list)
    ####################################################################
    note = fields.Html(string='Notes')
    owner_id = fields.Many2one('res.partner', string='Owner',)
    sequence = fields.Integer(default=10)

    block_count = fields.Integer(compute='_compute_site_stats', string='Blocks')
    building_count = fields.Integer(compute='_compute_site_stats', string='Buildings')
    unit_count = fields.Integer(compute='_compute_site_stats', string='Units')
    reservation_count = fields.Integer(compute='_compute_site_stats', string='Reservations')
    ownership_contract_count = fields.Integer(compute='_compute_site_stats', string='Sales contracts')
    # rental_contract_count = fields.Integer(compute='_compute_site_stats', string='Rental contracts')

    _sql_constraints = [
        ('site_code_company_uniq', 'unique(code, company_id)', 'Site code must be unique per company.'),
    ]
    ####################################################################
    # generate content for Kanban Card
    
    available_units_count = fields.Char(default='Available Units 20')
    sold_units_count = fields.Char(default='Sold Units 10')
    # unit_ids = fields.One2many('kx.property.tenant', 'property_id', string='Tenants')

    # available_units_count = fields.Integer(compute='_compute_units_stat', store=True)
    # sold_units_count = fields.Integer(compute='_compute_units_stat', store=True)
    # reserved_units_count = fields.Float(compute='_compute_units_stat', store=True)

    # @api.depends('tenant_ids', 'tenant_ids.state', 'tenant_ids.monthly_rent')
    # def _compute_tenant_stats(self):
    #     for rec in self:
    #         rec.tenant_count = len(rec.tenant_ids)
    #         rec.active_tenant_count = len( rec.tenant_ids.filtered( lambda t: t.state == 'active' ) )
    #         rec.total_rent = sum(rec.tenant_ids.mapped('monthly_rent'))
    
    ####################################################################
    @api.depends('block_ids', 'building_ids')
    def _compute_site_stats(self):
        for site in self:
            site.block_count = len(site.block_ids)
            site.building_count = len(site.building_ids)
        if not self.ids:
            for site in self:
                site.unit_count = 0
                site.reservation_count = 0
                site.ownership_contract_count = 0
                # site.rental_contract_count = 0
            return
        Unit = self.env['product.template']
        Res = self.env['unit.reservation']
        Own = self.env['ownership.contract']
        # Rent = self.env['rental.contract']

        def grouped_counts(model, field_name):
            return {
                g[field_name][0]: g['__count']
                for g in model.read_group(
                    [(field_name, 'in', self.ids)], ['__count'], [field_name], lazy=False
                )
                if g.get(field_name)
            }

        umap_prop = {
            g['site_id'][0]: g['__count']
            for g in Unit.read_group(
                [('site_id', 'in', self.ids), ('is_property', '=', True)],
                ['__count'],
                ['site_id'],
                lazy=False,
            )
            if g.get('site_id')
        }
        rmap = grouped_counts(Res, 'site_id')
        omap = grouped_counts(Own, 'site_id')
        # rent_map = grouped_counts(Rent, 'site_id')
        for site in self:
            site.unit_count = umap_prop.get(site.id, 0)
            site.reservation_count = rmap.get(site.id, 0)
            site.ownership_contract_count = omap.get(site.id, 0)
            # site.rental_contract_count = rent_map.get(site.id, 0)
    ################################################################################
    def _action_window(self, name, res_model, domain, context=None):
        self.ensure_one()
        action = {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }
        if context:
            action['context'] = context
        return action
    ##################################################################################
    def action_view_blocks(self):
        self.ensure_one()
        return self._action_window(_('Blocks'), 're.block', [('site_id', '=', self.id)], {'default_site_id': self.id})
    ##################################################################################
    def action_view_buildings(self):
        self.ensure_one()
        return self._action_window(
            _('Buildings'),
            'building.building',
            [('site_id', '=', self.id)],
            {'default_site_id': self.id},
        )
    ####################################################################################
    def action_view_units(self):
        self.ensure_one()
        return self._action_window(
            _('Units'),
            'product.template',
            [('site_id', '=', self.id), ('is_property', '=', True)],
            {'default_is_property': True},
        )
    ####################################################################################
    def action_view_reservations(self):
        self.ensure_one()
        return self._action_window(_('Reservations'), 'unit.reservation', [('site_id', '=', self.id)])
    ####################################################################################
    def action_view_ownership_contracts(self):
        self.ensure_one()
        return self._action_window(_('Ownership contracts'), 'ownership.contract', [('site_id', '=', self.id)])
    ####################################################################################
    # def action_view_rental_contracts(self):
    #     self.ensure_one()
    #     return self._action_window(_('Rental contracts'), 'rental.contract', [('site_id', '=', self.id)])
