# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_manufacture_spec_ids = fields.One2many('product.manufacture.specification', 'purchase_line_id', string='Finished Product Specifications')

    @api.constrains('product_manufacture_spec_ids')
    def _check_product_manufacture_spec_one2one(self):
        """
        The link between a MO and its product manufacture spec should be a one2one relationship.
        Make sure that no more than one product manufacture spec is linked to a MO.
        """
        for purchase_line in self:
            if purchase_line.product_manufacture_spec_ids and len(purchase_line.product_manufacture_spec_ids) > 1:
                raise UserError(_('PO line should not have more than one Finished Product Specification. See PO line({})').format(purchase_line.name_get()))
