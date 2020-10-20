# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from math import ceil
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCBom(models.Model):
    _inherit = 'mrp.bom'

    does_produce_mothersheet = fields.Boolean(string='Mothersheet', default=False, help='Flag this option if this bom consume DLS and produce mothersheet.')
    mothersheet_length = fields.Float(string='Mothersheet Length (mm)', default=0.0)
    mothersheet_width = fields.Float(string='Mothersheet Width (mm)', default=0.0)
    product_id = fields.Many2one('product.product', required=True)
    product_qty = fields.Float(help='MO created during the MTO process from this BOM will have a \'Quantity To Produce\' that is a factor of this quantity.')

    @api.constrains('efficiency')
    def _check_efficiency_domain(self):
        """
        Make sure that efficiency is in the range ]0; 100].
        """
        for bom in self:
            if not 0 < bom.efficiency <= 100:
                raise UserError(_('The Yield must be greater than 0 and lower or equal than 100.'))

    def explode(self, product, quantity, picking_type=False):
        """
        Overridden method
        change quantity parameter in order to compute the right factor with product per mothersheet and bom efficiency
        """
        if 'production_id' in self.env.context:
            production = self.env['mrp.production'].browse(self.env.context.get('production_id'))
            done_moves = production.move_finished_ids.filtered(lambda x: x.state == 'done' and x.product_id == production.product_id)
            qty_produced = production.product_id.uom_id._compute_quantity(sum(done_moves.mapped('product_qty')), production.product_uom_id)
            if production.product_id.categ_id.product_type == 'finished_product' and production.product_manufacture_step_ids:
                qty_needed = production.product_uom_id._compute_quantity(production.product_qty - qty_produced, production.bom_id.product_uom_id)
                product_per_ms = production.product_manufacture_step_ids.sale_line_id.finished_product_quantity
                factor = ceil(qty_needed / product_per_ms) / production.bom_id.product_qty
            else:
                factor = production.product_uom_id._compute_quantity(production.product_qty - qty_produced, production.bom_id.product_uom_id) / production.bom_id.product_qty
            factor = ceil(factor * (100 / production.product_manufacture_step_ids.bom_efficiency or 1))
            # use factor just for disambiguation purpose
            quantity = factor
        return super(AGCBom, self).explode(product, quantity, picking_type)
