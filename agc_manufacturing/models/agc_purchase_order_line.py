# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AGCPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_manufacture_spec_ids = fields.One2many('product.manufacture.specification', 'purchase_line_id', string='Finished Product Specifications')

    @api.constrains('product_manufacture_spec_ids')
    def product_manufacture_spec_one2one(self):
        """
        The link between an MO and its product manufacture spec should be a one2one.
        Make sure that no more than one product manufacture spec is linked to an MO.
        """
        for purchase_line in self:
            if purchase_line.product_manufacture_spec_ids and len(purchase_line.product_manufacture_spec_ids) > 1:
                raise UserError(_('An MO should not have more than one Finished Product Specifications. See MO(%s)' % purchase_line.name))
