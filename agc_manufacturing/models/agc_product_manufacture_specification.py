# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AGCProductManufactureSpecification(models.Model):
    _name = 'product.manufacture.specification'
    _description = 'Each record describe a step of the manufacturing chain aiming to produced a finished product.'
    _order = 'sequence'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', required=True, ondelete='cascade')
    configuration_is_done = fields.Boolean(related='sale_line_id.configuration_is_done', string='FP Configuration is done', help='Technical field that helps to know whether the Finished Product configuration is done.')
    sale_order_state = fields.Selection(related='sale_line_id.order_id.state', string='Sale Order Status')
    sequence = fields.Integer(string='Sequence', help="Used to order the 'Product specification' tree view")
    product_id = fields.Many2one('product.product', string='Product')
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material')
    bom_efficiency = fields.Integer(string="BoM's Yield (%)", default=100)
    routing_id = fields.Many2one('mrp.routing', string="Routing")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string="Routing's Complexity")
    currency_id = fields.Many2one('res.currency', related='sale_line_id.currency_id')
    price_unit = fields.Monetary(string='Unit Cost', default=0.0)
    origin_manufacture_spec_id = fields.Many2one('product.manufacture.specification', string="Origin Product Specification", help='Technical field that indicate which specification has triggered the creation of this record.')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    production_status = fields.Selection(related='production_id.state', string='MO Status')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    purchase_id = fields.Many2one('purchase.order', related='purchase_line_id.order_id', string='Purchase Order')

    @api.constrains('bom_efficiency')
    def efficiency_domain(self):
        """
        Make sure that the efficiency is in the range ]0; 100]
        """
        for product_specifiaction in self:
            if not 0 < product_specifiaction.bom_efficiency <= 100:
                raise UserError(_("The BOM's yield must be greater than 0 or lower/equal to 100."))
