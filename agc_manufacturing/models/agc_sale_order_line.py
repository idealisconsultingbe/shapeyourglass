# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AGCSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    button_configure_visible = fields.Boolean(string='Configure Finished Product Button Visibility', compute='_compute_button_configure_visible', help='Technical field used to compute finished product button visibility.')
    product_manufacture_step_ids = fields.One2many('product.manufacturing.step', 'sale_line_id', string='Finished Product Manufacturing Step')
    finished_product_unit_cost = fields.Monetary(string='Finished Product Unit Cost', readonly=True, default=0.0)
    finished_product_quantity = fields.Integer(string='Finished Products / Mothersheet', default=1)
    configuration_is_done = fields.Boolean(string='Finished Product Configuration is Done', default=False, help='Technical field that helps to know whether the Finished Product configuration is done.')

    @api.depends('product_id.categ_id.product_type')
    def _compute_button_configure_visible(self):
        """
        Check whether the product selected is a finished product.
        If it is it should be configured.
        """
        for line in self:
            if line.product_id.categ_id.product_type == 'finished_product':
                line.button_configure_visible = True
            else:
                line.button_configure_visible = False

    @api.onchange('finished_product_quantity')
    def _onchange_finished_product_quantity(self):
        for line in self:
            if line.finished_product_unit_cost > 0.0:
                self.calculate_product_cost_action()

    def open_fp_configuration_view(self):
        """
        Return a different view depending on whether the SO is confirmed or not
        """
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            view_id = self.env.ref('agc_manufacturing.sale_order_line_view_form').id
        else:
            view_id = self.env.ref('agc_manufacturing.sale_order_line_confirmed_view_form').id

        if not self.product_manufacture_step_ids.filtered(lambda step: step.sale_line_id == self):
            vals = {
                'product_id': self.product_id.id,
                'sequence': 1,
                'sale_line_id': self.id
            }
            product_manufacture_step_id = self.env['product.manufacturing.step'].create(vals)
            self.write({'product_manufacture_step_ids': [(6, 0, [product_manufacture_step_id.id])]})
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order.line',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'new',
        }

    def find_next_unlinked_manufacturing_step(self, product_id, subcontracted=False):
        """
        Return the next manufacturing step not linked to an MO.
        If the product given does not match the product of the next manufacturing step return an Error.
        """
        self.ensure_one()
        for step_line in self.product_manufacture_step_ids.sorted(key=lambda step: step.sequence):
            if not step_line.production_id:
                if step_line.product_id != product_id:
                    raise ValidationError(_('Product ({}) is not the one expected ({} expected)').format(step_line.product_id.name_get(), product_id.name_get()))
                elif subcontracted and step_line.bom_id.type != 'subcontract':
                    raise ValidationError(_('the BOM {} is not of type subcontract').format(step_line.bom_id.name))
                else:
                    return step_line
        return False

    def _get_last_manufacturing_step(self):
        """
        :return: The last manufacturing step, the one with the higher sequence.
        """
        sorted_steps = self.product_manufacture_step_ids.sorted(key=lambda step: step.sequence, reverse=True)
        return sorted_steps[0] if sorted_steps else False

    def _reset_prices(self):
        self.finished_product_unit_cost = 0.0
        self.product_manufacture_step_ids.write({'price_unit': 0.0})

    def calculate_product_cost_action(self):
        """
        At each manufacturing step calculate the unit cost of the manufactured product.
        This cost depends on the components consumed during the manufacturing process + the hourly rate * the expected time set on the workcenters used.
        """
        self.ensure_one()
        if not self.configuration_is_done:
            return {'warning': _('Product ({}) configuration is not done yet.').format(self.product_id.name_get())}
        else:
            sorted_steps = self.product_manufacture_step_ids.sorted(key=lambda step: step.sequence, reverse=True)
            if not sorted_steps:
                return self.open_fp_configuration_view()
            elif len(sorted_steps) == 1:
                step_line = sorted_steps[0]
                work_center_cost = sum([(operation.time_cycle_manual / 60.0) * operation.workcenter_id.costs_hour for operation in step_line.routing_id.operation_ids])
                bom_line_price = sum([line.product_id.standard_price * line.product_qty for line in step_line.bom_id.bom_line_ids])
                bom_efficiency = step_line.bom_efficiency/100 or 1
                routing_efficiency = step_line.routing_efficiency_id.efficiency/100 or 1
                bom_qty = step_line.bom_id.product_qty or 1
                step_line.price_unit = (bom_line_price + work_center_cost) / bom_efficiency / routing_efficiency / bom_qty
                self.finished_product_unit_cost = step_line.price_unit / (self.finished_product_quantity or 1)
            else:
                products_price_list = {}
                for step_line in sorted_steps:
                    work_center_cost = sum([(operation.time_cycle_manual / 60.0) * operation.workcenter_id.costs_hour for operation in step_line.routing_id.operation_ids])
                    semi_finished_product_bom_lines = step_line.bom_id.bom_line_ids.filtered(lambda line: line.product_id.categ_id.product_type == 'semi_finished_product')
                    other_products_bom_lines = step_line.bom_id.bom_line_ids - semi_finished_product_bom_lines
                    semi_finished_product_bom_lines_price = sum([products_price_list.get(line.product_id.id, 0) * line.product_qty for line in semi_finished_product_bom_lines])
                    other_products_bom_lines_price = sum([line.product_id.standard_price * line.product_qty for line in other_products_bom_lines])
                    bom_efficiency = step_line.bom_efficiency / 100 or 1
                    routing_efficiency = step_line.routing_efficiency_id.efficiency / 100 or 1
                    bom_qty = step_line.bom_id.product_qty or 1
                    step_line.price_unit = (other_products_bom_lines_price + semi_finished_product_bom_lines_price + work_center_cost) / bom_efficiency / routing_efficiency / bom_qty
                    products_price_list[step_line.product_id.id] = step_line.price_unit
                    self.finished_product_unit_cost = step_line.price_unit / (self.finished_product_quantity or 1)
            return self.open_fp_configuration_view()
