# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AGCRouting(models.Model):
    _inherit = 'mrp.routing'

    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('bom_ids', '!=', False), ('bom_ids.active', '=', True), ('bom_ids.type', '=', 'normal'), ('type', 'in', ['product', 'consu'])]")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string="Routing's Complexity", help='This parameter allows to adapt the efficiency of the Routing, its value must be comprised between 0 and 100.'
                                                                                                          'If the complexity as an efficiency lower than 100 it will impact the evaluation of the cost of the manufacturing process.'
                                                                                                          'It will also impact the quantity of raw materials send to the manufacturing location.')
