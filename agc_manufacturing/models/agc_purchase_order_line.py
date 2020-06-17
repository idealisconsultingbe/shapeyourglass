# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_manufacture_step_ids = fields.One2many('product.manufacturing.step', 'purchase_line_id', string='Finished Product Manufacturing Step')

    @api.constrains('product_manufacture_step_ids')
    def _check_product_manufacture_step_one2one(self):
        """
        The link between a MO and its product manufacturing step should be a one2one relationship.
        Make sure that no more than one product manufacture step is linked to a MO.
        """
        for purchase_line in self:
            if len(purchase_line.product_manufacture_step_ids or []) > 1:
                raise UserError(_('PO line should not have more than one Finished Product Manufacturing Step. See PO line({})').format(purchase_line.name_get()))
