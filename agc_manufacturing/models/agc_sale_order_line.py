# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AGCSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_manufacture_spec_ids = fields.One2many('product.manufacture.specification', 'sale_line_id', string='Finished Product Specifications')
    finished_product_unit_cost = fields.Monetary(string='Finished Product Unit Cost', default=0.0)
    finished_product_quantity = fields.Integer(string='Quantity', default=0)
