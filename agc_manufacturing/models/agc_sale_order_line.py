# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AGCSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_manufacture_spec_ids = fields.One2many('product.manufacture.specification', 'sale_line_id', string='Finished Product Specifications')
    finished_product_unit_cost = fields.Monetary(string='Finished Product Unit Cost', default=0.0)
    finished_product_quantity = fields.Integer(string='Mothersheet / DLS', default=0)
    configuration_is_done = fields.Boolean(string='FP Configuration is done', default=False, help='Technical field that helps to know whether the Finished Product configuration is done.')

    def open_fp_configuration_view(self):
        """
        Return a different view depending on whether the SO is confirmed.
        """
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            view_id = self.env.ref('agc_manufacturing.sale_order_line_form_product_manufacture_spec_view').id
        else:
            view_id = self.env.ref('agc_manufacturing.sale_order_line_confirmed_form_product_manufacture_spec_view').id
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order.line',
            'view_id': view_id,
            'target': 'new',
        }
