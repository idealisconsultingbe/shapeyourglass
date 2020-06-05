# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AGCProductManufactureSpecification(models.Model):
    _name = 'product.manufacture.specification'
    _description = 'Each record describes a step of the manufacturing chain aiming to produced a finished product.'
    _order = 'sequence'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', required=True, ondelete='cascade')
    configuration_is_done = fields.Boolean(related='sale_line_id.configuration_is_done', string='Finished Product Configuration is Done', help='Technical field that helps to know whether the Finished Product configuration is done.')
    sale_order_state = fields.Selection(related='sale_line_id.order_id.state', string='Sale Order Status')
    sequence = fields.Integer(string='Sequence', help="Used to order the 'Product specification' tree view")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', domain="[('product_id', '=', product_id), ('active', '=', True)]")
    bom_efficiency = fields.Integer(string='BoM  Yield (%)', help='This parameter allows to adapt BOM efficiency. Its value must be lower or equal to 100 and higher than zero.'
                                                                                'A value lower than 100 will impact cot evaluation of the manufacturing process.'
                                                                                'It will also impact the quantity of raw material send to the manufacturing location.')
    routing_id = fields.Many2one('mrp.routing', string='Routing', domain="[('product_id', '=', product_id), ('active', '=', True)]")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string='Routing Complexity', help='This parameter allows to adapt Routing efficiency, its value must be included between 0 and 100.'
                                                                                                          'If complexity as an efficiency lower than 100 it will impact cost evaluation of the manufacturing process.'
                                                                                                          'It will also impact the quantity of raw material send to the manufacturing location.')
    currency_id = fields.Many2one('res.currency', related='sale_line_id.currency_id', string='Currency')
    price_unit = fields.Monetary(string='Unit Cost', default='0.0')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    production_status = fields.Selection(related='production_id.state', string='MO Status', help='Display the status of the Manufacturing Order')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    purchase_id = fields.Many2one('purchase.order', related='purchase_line_id.order_id', string='Purchase Order')
    state = fields.Selection([('to_update', 'To Update'), ('updated', 'Updated'), ('locked', 'Locked')], string='status', default='to_update')

    @api.constrains('bom_efficiency')
    def _check_efficiency_domain(self):
        """
        Make sure that efficiency is in ]0; 100] range
        """
        for product_specification in self:
            if not 0 < product_specification.bom_efficiency <= 100:
                raise UserError(_('The BOM yield must be greater than 0 and lower or equal than 100.'))

    @api.onchange('routing_id')
    def _onchange_routing_id(self):
        if self.routing_id:
            self.routing_efficiency_id = self.routing_id.routing_efficiency_id or self.routing_efficiency_id

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.bom_efficiency = self.bom_id.efficiency or self.bom_efficiency

    def update_product_specification_action(self):
        self.ensure_one()
        if self.bom_id and self.routing_id:
            bom_semi_finished_products = self.bom_id.bom_line_ids.filtered(
                lambda line: line.product_id.categ_id.product_type == 'semi_finished_product')
            if len(bom_semi_finished_products) > 1:
                error_msg = _('{} BoM has more than one semi-finished product in its components list').format(self.bom_id)
                raise ValidationError(error_msg)
            elif bom_semi_finished_products:
                self.state = 'locked'
                vals = {
                    'product_id': bom_semi_finished_products.product_id.id,
                    'sequence': self.sequence + 1,
                    'sale_line_id': self.sale_line_id.id,
                }
                self.sale_line_id.update({'product_manufacture_spec_ids': [(0, 0, vals)]})
            else:
                self.state = 'updated'
                self.sale_line_id.configuration_is_done = True
        return self.sale_line_id.open_fp_configuration_view()

    def delete_product_specification_action(self):
        sale_line = self.sale_line_id
        # after this, we lose references to self
        sale_line.update({'product_manufacture_spec_ids': [(2, self.id, 0)]})
        # retrieve last product specification and set its state to updatable
        if sale_line._get_last_product_spec():
            sale_line._get_last_product_spec().state = 'to_update'
        # reset configuration done flag
        sale_line.configuration_is_done = False
        # reset calculated prices
        sale_line._reset_prices()
        # return view
        return sale_line.open_fp_configuration_view()
