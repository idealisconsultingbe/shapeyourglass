# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AGCProduct(models.Model):
    _inherit = 'product.product'

    routing_ids = fields.One2many('mrp.routing', 'product_id', string="Routings")
