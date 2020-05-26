# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AGCProductCategory(models.Model):
    _inherit = 'product.category'

    PRODUCT_TYPES = [('finished_product', 'Finished Product'),
                     ('semi_finished_product', 'Semi-Finished Product'),
                     ('other', 'Other')]
    product_type = fields.Selection(PRODUCT_TYPES, string='Product Type', default='other')
