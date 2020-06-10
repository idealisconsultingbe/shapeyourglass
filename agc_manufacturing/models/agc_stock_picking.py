# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import ValidationError


class AGCStockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_sale_order_line(self, moves):
        for move in moves:
            if move.sale_line_id:
                return move.sale_line_id
            elif move.raw_material_production_id:
                if len(move.raw_material_production_id.move_dest_ids or []) == 1:
                    return self._get_sale_order_line(move.raw_material_production_id.move_dest_ids)
                elif len(move.raw_material_production_id.move_finished_ids or []) == 1:
                    return self._get_sale_order_line(move.raw_material_production_id.move_finished_ids)
                else:
                    return False
            elif len(move.move_dest_ids or []) == 1:
                return self._get_sale_order_line(move.move_dest_ids)
            else:
                return False

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        """ Overridden Method """
        res = super(AGCStockPicking, self)._prepare_subcontract_mo_vals(subcontract_move, bom)
        if self.env.context.get('pf_configure', False):
            so_line = self._get_sale_order_line(subcontract_move.move_dest_ids)
            if so_line:
                for spec_line in so_line.product_manufacture_spec_ids.sorted(key=lambda spec: spec.sequence):
                    if not spec_line.production_id:
                        if spec_line.bom_id.type == 'subcontract' and spec_line.product_id != subcontract_move.product_id:
                            raise ValidationError(
                                _('Product ({}) is not the one expected ({} expected or the BOM {} is not of type subcontract.)').format(spec_line.product_id.name_get(), self.product_id.name_get(), spec_line.bom_id.name))
                        else:
                            res['product_manufacture_spec_ids'] = [(4, spec_line.id, 0)]
                            break
        return res
