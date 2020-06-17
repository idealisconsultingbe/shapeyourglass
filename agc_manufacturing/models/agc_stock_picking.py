# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import ValidationError


class AGCStockPicking(models.Model):
    _inherit = 'stock.picking'

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        """
        Overridden Method
        Linked the subcontracted MO to its destination move.
        We also linked the subcontracted MO to its manufacturing step.
        """
        res = super(AGCStockPicking, self)._prepare_subcontract_mo_vals(subcontract_move, bom)
        if self.env.context.get('pf_configure', False):
            res.update({'subcontract_move_dest_id': subcontract_move.id})
            so_line = subcontract_move.move_dest_ids._get_sale_order_line() if subcontract_move.move_dest_ids else False
            if so_line:
                spec_line = so_line.find_next_unlinked_product_spec(subcontract_move.product_id, subcontracted=True)
                if spec_line:
                    res['product_manufacture_spec_ids'] = [(4, spec_line.id, 0)]
        return res
