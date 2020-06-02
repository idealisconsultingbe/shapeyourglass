# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AGCStockMove(models.Model):
    _inherit = 'stock.move'

    def _create_out_svl(self, forced_quantity=None):
        """
        The standard method has been override in order to compute the valuation of a stock.valuation.layer depending on
        lots and their unit cost. If the move has several line with lots we take as valuation the average cost of every line.
        """
        svl = super(AGCStockMove, self)._create_out_svl(forced_quantity)
        for valuation in svl:
            does_lot_has_unit_cost = any(valuation.stock_move_id.move_line_ids.mapped('lot_id.unit_cost'))
            # If at least one stock move line has a move with a unit_cost we alter the unit_cost of the created svl.
            if does_lot_has_unit_cost:
                total_cost = 0
                total_done_qty = 0
                for line in valuation.stock_move_id.move_line_ids:
                    lot_id = line.lot_id
                    line_quantity = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
                    total_done_qty += line_quantity
                    if lot_id and lot_id.unit_cost > 0:
                        total_cost += lot_id.unit_cost * line_quantity
                    else:
                        total_cost += valuation.product_id.standard_price * line_quantity
                valuation.unit_cost = total_cost / total_done_qty
                valuation.value = valuation.unit_cost * valuation.quantity
        return svl
