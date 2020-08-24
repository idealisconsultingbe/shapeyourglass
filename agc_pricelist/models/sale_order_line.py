# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, values):
        if 'purchase_price' in values:
            if self.order_id.pricelist_id and self.order_id.pricelist_id.discount_policy == 'with_discount' and self.order_id.partner_id and self.product_id:
                final_price, rule_id = self.order_id.pricelist_id.with_context(line_cost=values['purchase_price']).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
                values['price_unit'] = final_price
        return super(SaleOrderLine, self).write(values)

    @api.onchange('purchase_price')
    def _onchange_purchase_price(self):
        if self.order_id.pricelist_id and self.order_id.pricelist_id.discount_policy == 'with_discount' and self.order_id.partner_id and self.product_id:
            final_price, rule_id = self.order_id.pricelist_id.with_context(line_cost=self.purchase_price).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
            self.update({'price_unit': final_price})
