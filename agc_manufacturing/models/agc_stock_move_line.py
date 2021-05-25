# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


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
                product = production.move_raw_ids.mapped('move_line_ids')[0].product_id if production.move_raw_ids.mapped('move_line_ids') else False
                thickness = 0.0
                if product and product.product_template_attribute_value_ids:
                    ptav_thickness = product.product_template_attribute_value_ids.filtered(lambda ptav: ptav.attribute_id.is_a_dimension and ptav.attribute_id.dimension_type == 'thickness')
                    try:
                        thickness = float(ptav_thickness[0].product_attribute_value_id.name) if ptav_thickness else 0.0
                    except ValueError:
                        raise UserError(_('Invalid thickness value format: cannot convert {} to float.').format(ptav_thickness[0].product_attribute_value_id.name))

                if production.width and production.length:
                    length = production.length
                    width = production.width
                elif production.bom_id.does_produce_mothersheet:
                    length = production.bom_id.mothersheet_length
                    width = production.bom_id.mothersheet_width
                else:
                    length = lot_component.length if lot_component else 0.0
                    width = lot_component.width if lot_component else 0.0

                    if not length and product and product.product_template_attribute_value_ids:
                        ptav_length = product.product_template_attribute_value_ids.filtered(lambda ptav: ptav.attribute_id.is_a_dimension and ptav.attribute_id.dimension_type == 'length')
                        try:
                            length = float(ptav_length[0].product_attribute_value_id.name) if ptav_length else 0.0
                        except ValueError:
                            raise UserError(_('Invalid length value format: cannot convert {} to float.').format(
                                ptav_thickness[0].product_attribute_value_id.name))
                    if not width and product and product.product_template_attribute_value_ids:
                        ptav_width = product.product_template_attribute_value_ids.filtered(lambda ptav: ptav.attribute_id.is_a_dimension and ptav.attribute_id.dimension_type == 'width')
                        try:
                            width = float(ptav_width[0].product_attribute_value_id.name) if ptav_width else 0.0
                        except ValueError:
                            raise UserError(_('Invalid width value format: cannot convert {} to float.').format(
                                ptav_thickness[0].product_attribute_value_id.name))

                sml.lot_id.write({
                    'length': length,
                    'width': width,
                    'thickness': lot_component.thickness if lot_component and lot_component.thickness > 0 else thickness,
                    'bom_ids': [(6, 0, [production.bom_id.id] + (lot_component.bom_ids.ids if lot_component and lot_component.bom_ids else []))],
                    'routing_ids': [(6, 0, [production.routing_id.id] + (lot_component.routing_ids.ids if lot_component and lot_component.routing_ids else []))]
                })
        return super(StockMoveLine, self)._action_done()
