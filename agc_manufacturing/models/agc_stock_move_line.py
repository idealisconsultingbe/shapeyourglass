# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AGCStockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _set_product_qty(self):
        """ Overwritten method in order to prevent error to be raised """
        return True
