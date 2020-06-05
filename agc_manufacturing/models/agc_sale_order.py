# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import models


class AGCSaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        """ Overridden Method """
        if self.order_line.filtered(lambda line: line.product_id.categ_id.product_type == 'finished_product'):
            self = self.with_context(pf_configure=True)
        return super(AGCSaleOrder, self).action_confirm()