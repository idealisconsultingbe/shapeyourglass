# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AGCRouting(models.Model):
    _inherit = 'mrp.routing'

    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('bom_ids', '!=', False), ('bom_ids.active', '=', True), ('bom_ids.type', '=', 'normal'), ('type', 'in', ['product', 'consu'])]")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string="Routing's Complexity")
