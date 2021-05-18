# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        """
        Overridden method called during a move's `action_done`.

        Add information to stock production lot linked to stock move lines. Those information
        are used to filter stock production lots according to width, length, thickness, routes used or BoMs used.
        Those information come from configurated sale order lines or bill of materials.
        """
        for sml in self:
            production = sml.move_id.production_id
            if sml.lot_id and production:
                lot_component = production.move_raw_ids.mapped('move_line_ids')[0].lot_id if production.move_raw_ids.mapped('move_line_ids') else False
                if production.width and production.length:
                    length = production.length
                    width = production.width
                elif production.bom_id.does_produce_mothersheet:
                    length = production.bom_id.mothersheet_length
                    width = production.bom_id.mothersheet_width
                else:
                    length = lot_component.length
                    width = lot_component.width
                sml.lot_id.write({
                    'length': length,
                    'width': width,
                    'thickness': lot_component.thickness if lot_component else 0.0,
                    'bom_ids': [(6, 0, [production.bom_id.id] + (lot_component.bom_ids.ids if lot_component and lot_component.bom_ids else []))],
                    'routing_ids': [(6, 0, [production.routing_id.id] + (lot_component.routing_ids.ids if lot_component and lot_component.routing_ids else []))]
                })
        return super(StockMoveLine, self)._action_done()
