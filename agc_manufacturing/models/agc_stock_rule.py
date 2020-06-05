# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import ValidationError


class AGCStockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_sale_order_line(self, moves):
        for move in moves:
            if move.sale_line_id:
                return move.sale_line_id
            elif len(move.move_dest_ids) == 1:
                return self._get_sale_order_line(move.move_dest_ids)
            else:
                return False

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        res = super(AGCStockRule, self)._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        if self.env.context.get('pf_configure', False):
            so_line = self._get_sale_order_line(values.get('move_dest_ids', []))
            if so_line:
                for spec_line in so_line.product_manufacture_spec_ids.sorted(key=lambda spec: spec.sequence):
                    if not spec_line.purchase_line_id and not spec_line.production_id:
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
