from odoo import api, fields, models, _


class RealEstateBlock(models.Model):
    _name = "re.block"
    _description = "Real Estate Block"
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    active = fields.Boolean(default=True)
    building_ids = fields.One2many('building.building', 'block_id', string='Buildings')
    code = fields.Char(string='Code', tracking=True, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    name = fields.Char(required=True, tracking=True)
    note = fields.Html(string='Notes')
    sequence = fields.Integer(default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals.get('code') == '/':
                site = self.env['re.site'].browse(vals.get('site_id'))
                prefix = site.code + '/' if site and site.code else ''
                vals['code'] = prefix + (self.env['ir.sequence'].next_by_code('re.block') or '/')
        return super().create(vals_list)
    site_id = fields.Many2one('re.site', string='Site', required=True, ondelete='cascade', tracking=True)

    building_count = fields.Integer(compute='_compute_block_stats', string='Buildings')
    unit_count = fields.Integer(compute='_compute_block_stats', string='Units')
    reservation_count = fields.Integer(compute='_compute_block_stats', string='Reservations')
    ownership_contract_count = fields.Integer(compute='_compute_block_stats', string='Sales contracts')
    # rental_contract_count = fields.Integer(compute='_compute_block_stats', string='Rental contracts')

    _sql_constraints = [
        ('block_code_site_uniq', 'unique(code, site_id)', 'Block code must be unique per site.'),
    ]

    @api.depends('building_ids')
    def _compute_block_stats(self):
        for block in self:
            block.building_count = len(block.building_ids)
        if not self.ids:
            for block in self:
                block.unit_count = 0
                block.reservation_count = 0
                block.ownership_contract_count = 0
                # block.rental_contract_count = 0
            return
        Unit = self.env['product.template']
        Res = self.env['unit.reservation']
        Own = self.env['ownership.contract']
        # Rent = self.env['rental.contract']

        umap_prop = {
            g['block_id'][0]: g['__count']
            for g in Unit.read_group(
                [('block_id', 'in', self.ids), ('is_property', '=', True)],
                ['__count'],
                ['block_id'],
                lazy=False,
            )
            if g.get('block_id')
        }
        rmap = {
            g['block_id'][0]: g['__count']
            for g in Res.read_group(
                [('block_id', 'in', self.ids)], ['__count'], ['block_id'], lazy=False
            )
            if g.get('block_id')
        }
        omap = {
            g['block_id'][0]: g['__count']
            for g in Own.read_group(
                [('block_id', 'in', self.ids)], ['__count'], ['block_id'], lazy=False
            )
            if g.get('block_id')
        }
        # rent_map = {
        #     g['block_id'][0]: g['__count']
        #     for g in Rent.read_group(
        #         [('block_id', 'in', self.ids)], ['__count'], ['block_id'], lazy=False
        #     )
        #     if g.get('block_id')
        # }
        for block in self:
            block.unit_count = umap_prop.get(block.id, 0)
            block.reservation_count = rmap.get(block.id, 0)
            block.ownership_contract_count = omap.get(block.id, 0)
            # block.rental_contract_count = rent_map.get(block.id, 0)

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

    def action_view_buildings(self):
        self.ensure_one()
        return self._action_window(
            _('Buildings'),
            'building.building',
            [('block_id', '=', self.id)],
            {'default_block_id': self.id, 'default_site_id': self.site_id.id},
        )

    def action_view_units(self):
        self.ensure_one()
        return self._action_window(
            _('Units'),
            'product.template',
            [('block_id', '=', self.id), ('is_property', '=', True)],
            {'default_is_property': True, 'default_block_id': self.id},
        )

    def action_view_reservations(self):
        self.ensure_one()
        return self._action_window(_('Reservations'), 'unit.reservation', [('block_id', '=', self.id)])

    def action_view_ownership_contracts(self):
        self.ensure_one()
        return self._action_window(_('Ownership contracts'), 'ownership.contract', [('block_id', '=', self.id)])

    # def action_view_rental_contracts(self):
    #     self.ensure_one()
    #     return self._action_window(_('Rental contracts'), 'rental.contract', [('block_id', '=', self.id)])
