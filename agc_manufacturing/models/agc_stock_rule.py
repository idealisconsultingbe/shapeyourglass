# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, models, _
from odoo.exceptions import ValidationError


class AGCStockRule(models.Model):
    _inherit = 'stock.rule'

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

    def _get_purchase_order_line_spec_vals(self, product_id, values):
        vals = {}
        if self.env.context.get('pf_configure', False):
            so_line = self._get_sale_order_line(values.get('move_dest_ids', False))
            if so_line:
                for spec_line in so_line.product_manufacture_spec_ids.sorted(key=lambda spec: spec.sequence):
                    if spec_line.bom_id.type == 'subcontract' and spec_line.product_id == product_id:
                        vals['product_manufacture_spec_ids'] = [(4, spec_line.id, 0)]
                        break
        return vals

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        """ Overridden Method """
        res = super(AGCStockRule, self)._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        if self.env.context.get('pf_configure', False):
            so_line = self._get_sale_order_line(values.get('move_dest_ids', False))
            if so_line:
                for spec_line in so_line.product_manufacture_spec_ids.sorted(key=lambda spec: spec.sequence):
                    if not spec_line.production_id:
                        if spec_line.product_id != product_id:
                            raise ValidationError(_('Product ({}) is not the one expected ({} expected)').format(spec_line.product_id, product_id))
                        else:
                            res.update({
                                'bom_id': spec_line.bom_id.id,
                                'routing_id': spec_line.routing_id.id,
                                'product_manufacture_spec_ids': [(4, spec_line.id, 0)]
                            })
                            break
        return res

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        """ Overridden Method """
        res = super(AGCStockRule, self)._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        res.update(self._get_purchase_order_line_spec_vals(product_id, values))
        return res

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        """ Overridden Method """
        res = super(AGCStockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)
        res.update(self._get_purchase_order_line_spec_vals(product_id, values))
        return res
