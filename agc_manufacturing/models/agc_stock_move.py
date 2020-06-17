# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AGCStockMove(models.Model):
    _inherit = 'stock.move'

    def _get_sale_order_line(self):
        """
        Go through the linked stock moves in a bottom-up way in order to find an so line.
        """
        self.ensure_one()
        # return the first so line we find.
        if self.sale_line_id:
            return self.sale_line_id
        # if the stock move is a component of an MO go through the MO in order to find its stock move destination.
        elif self.raw_material_production_id:
            if len(self.raw_material_production_id.move_dest_ids or []) == 1:
                return self.raw_material_production_id.move_dest_ids._get_sale_order_line()
            # If the MO has no destination it could because its a subcontracted MO.
            elif self.raw_material_production_id.subcontract_move_dest_id:
                return self.raw_material_production_id.subcontract_move_dest_id._get_sale_order_line()
            else:
                return False
        # Try to find an so line with the next stock move.
        elif len(self.move_dest_ids or []) == 1:
            return self.move_dest_ids._get_sale_order_line()
        else:
            return False

    def _get_subcontract_bom(self):
        """
        Overridden Method
        If we are in the pf_configure process.
        Use the BoM specified in the manufacturing step linked to this subcontract demand.
        """
        res = super(AGCStockMove, self)._get_subcontract_bom()
        if self.env.context.get('pf_configure', False):
            so_line = self.move_dest_ids._get_sale_order_line() if self.move_dest_ids else False
            if so_line:
                # If an so line has been found return the BoM of the first spec_line which is not already linked to an MO
                spec_line = so_line.find_next_unlinked_product_spec(self.product_id, subcontracted=True)
                if spec_line:
                    return spec_line.bom_id
        return res

    def _create_out_svl(self, forced_quantity=None):
        """
        The standard method has been overridden in order to compute the valuation of a stock.valuation.layer depending on
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
