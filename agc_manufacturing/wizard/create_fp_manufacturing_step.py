# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CreateFPManufacturingStep(models.TransientModel):
    _name = 'create.fp.manufacturing.step'
    _description = 'Each record describes a step of the manufacturing chain aiming to produce a finished product.'
    _order = 'sequence'

    fp_sale_line_id = fields.Many2one('create.fp.sale.order.line', string='Sale Order Line', ondelete='cascade')
    configuration_is_done = fields.Boolean(related='fp_sale_line_id.configuration_is_done', string='Finished Product Configuration is Done', help='Technical field that helps to know whether the Finished Product configuration is done.')
    sequence = fields.Integer(string='Sequence', help="Used to order the 'Product Manufacturing Step' tree view", default=1)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material')
    bom_type = fields.Selection(related='bom_id.type', string='BoM Type')
    initial_bom_efficiency = fields.Integer(string='Initial BoM  Yield (%)', compute='_get_initial_bom_yield')
    bom_efficiency = fields.Integer(string='BoM  Yield (%)', default=100, help='This parameter allows to adapt BOM efficiency. Its value must be lower or equal to 100 and higher than zero.\n'
                                                                               'A value lower than 100 will impact the cost evaluation of the manufacturing process.\n'
                                                                               'It will also impact the quantity of raw materials send to the manufacturing location.\n')
    routing_id = fields.Many2one('mrp.routing', string='Routing', domain="[('product_id', '=', product_id), ('active', '=', True)]")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string='Routing Complexity', help='This parameter allows to adapt Routing efficiency, its value must be included between 0 and 100.\n'
                                                                                                        'If the complexity as an efficiency lower than 100 it will impact the cost evaluation of the manufacturing process.\n')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    state = fields.Selection([('to_update', 'To Update'), ('updated', 'Updated'), ('locked', 'Locked')], string='status', default='to_update')

    @api.depends('bom_id')
    def _get_initial_bom_yield(self):
        for manuf_step in self:
            if manuf_step.bom_id:
                sfp_bom_line = manuf_step.bom_id.bom_line_ids.filtered(lambda line: line.product_id.categ_id.product_type == 'semi_finished_product')
                sfp_qty = sfp_bom_line[0].product_qty if sfp_bom_line else 1
                manuf_step.initial_bom_efficiency = manuf_step.bom_id.product_qty / sfp_qty * 100
            else:
                manuf_step.initial_bom_efficiency = 0

    @api.constrains('bom_efficiency')
    def _check_efficiency_domain(self):
        """
        Make sure that efficiency is in the range ]0; 100]
        """
        for manufacturing_step in self:
            if not 0 < manufacturing_step.bom_efficiency <= 100:
                raise UserError(_('The BOM yield must be greater than 0 and lower or equal than 100.'))

    @api.onchange('routing_id')
    def _onchange_routing_id(self):
        """
        Pre-filled the routing efficiency with the efficiency specified on the routing.
        """
        if self.routing_id:
            self.routing_efficiency_id = self.routing_id.routing_efficiency_id or self.routing_efficiency_id
