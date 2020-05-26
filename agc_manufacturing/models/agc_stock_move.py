# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AGCStockMove(models.Model):
    _inherit = 'stock.move'

    def _create_out_svl(self, forced_quantity=None):
        """
        The standard method has been overriden in order to compute the valuation of a stock.valuation.layer depending on
        a lot and its unit cost, instead of its product like it is in Odoo standard
        """
        svl = super(AGCStockMove, self)._create_out_svl(forced_quantity=None)
        for valuation in svl:
            for line in valuation.stock_move_id.move_line_ids:
                lot_id = line.lot_id
                if lot_id and lot_id.unit_cost > 0:
                    valuation.unit_cost = lot_id.unit_cost
                    valuation.value = valuation.unit_cost*valuation.quantity
        return svl
