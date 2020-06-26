# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AGCRouting(models.Model):
    _inherit = 'mrp.routing'

    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('bom_ids', '!=', False), ('bom_ids.active', '=', True), ('bom_ids.type', '=', 'normal'), ('type', 'in', ['product', 'consu'])]")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string="Routing's Complexity", required=True, help='This parameter allows to adapt Routing efficiency, its value must be included between 0 and 100.\n'
                                                                                                                         'If the complexity has an efficiency lower than 100 it will impact the cost evaluation of the manufacturing process.\n')
