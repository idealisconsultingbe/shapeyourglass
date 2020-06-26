# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


rec = 0
def autoIncrement():
    global rec
    pStart = 1
    pInterval = 1
    if rec == 0:
        rec = pStart
    else:
        rec += pInterval
    return rec


class AgcStockTraceability(models.TransientModel):
    _inherit = 'stock.traceability.report'

    def _make_dict_move(self, level, parent_id, move_line, unfoldable=False):
        """
        Add lot internal reference in the dictionary
        """
        data = super(AgcStockTraceability, self)._make_dict_move(level, parent_id, move_line, unfoldable=unfoldable)
        data[0].update({'internal_ref': move_line.lot_id.ref})
        return data

    @api.model
    def _final_vals_to_lines(self, final_vals, level):
        """
        Overwrite standard method, we add lot internal reference in the report.
        """
        lines = []
        for data in final_vals:
            lines.append({
                'id': autoIncrement(),
                'model': data['model'],
                'model_id': data['model_id'],
                'parent_id': data['parent_id'],
                'usage': data.get('usage', False),
                'is_used': data.get('is_used', False),
                'lot_name': data.get('lot_name', False),
                'lot_id': data.get('lot_id', False),
                'reference': data.get('reference_id', False),
                'res_id': data.get('res_id', False),
                'res_model': data.get('res_model', False),
                'columns': [data.get('reference_id', False),
                            data.get('product_id', False),
                            data.get('date', False),
                            data.get('lot_name', False),
                            data.get('internal_ref', False), # This line has been added!
                            data.get('location_source', False),
                            data.get('location_destination', False),
                            data.get('product_qty_uom', 0)],
                'level': level,
                'unfoldable': data['unfoldable'],
            })
        return lines
