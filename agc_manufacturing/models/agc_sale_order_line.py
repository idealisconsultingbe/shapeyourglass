# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from math import ceil


class AGCSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _default_millimeters_uom_id(self):
        uom = self.env.ref('agc_manufacturing.product_uom_millimeter', raise_if_not_found=False)
        if not uom:
            uom = self.env['uom.uom'].search([('category_id', '=', self.env.ref('uom.uom_categ_length').id), ('factor', '=', '1000')], limit=1)
        return uom

    button_configure_visible = fields.Boolean(string='Configure Finished Product Button Visibility', compute='_compute_button_configure_visible', help='Technical field used to compute finished product button visibility.')
    product_manufacture_step_ids = fields.One2many('product.manufacturing.step', 'sale_line_id', string='Finished Product Manufacturing Step')
    finished_product_quantity = fields.Integer(string='Finished Products / Mothersheet', default=1, help='Must be expressed in the unit of measure of the BoM selected for producing the Finished Product (the UoM of the BoM selected at the first line.)')
    max_producible_quantity = fields.Integer(string='Max Producible Qty', compute='_compute_max_producible_qty', help='The quantity which is going to be produced if we have an efficiency of 100% for each step.')
    configuration_is_done = fields.Boolean(string='Finished Product Configuration is Done', default=False, copy=False, help='Technical field that helps to know if the Finished Product configuration is done.')
    stock_move_ids = fields.One2many('stock.move', 'sale_order_line_id', string='Stock Moves', readonly=True)

    mothersheet_length = fields.Float(string='Mothersheet Length (mm)', compute='_compute_mothersheet_size', store=True)
    mothersheet_width = fields.Float(string='Mothersheet Width (mm)', compute='_compute_mothersheet_size', store=True)
    length = fields.Float(string='Final Product Length (mm)', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, default=0.0)
    width = fields.Float(string='Final Product Width (mm)', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, default=0.0)
    raw_product_ids = fields.Many2many('product.product', string='Raw Products', compute='_compute_raw_product_ids', store=True)
    route_ids = fields.Many2many('mrp.routing', string='Routings', compute='_compute_manufacturing_steps_operation', store=True)
    bom_ids = fields.Many2many('mrp.bom', string='Bill of Materials', compute='_compute_manufacturing_steps_operation', store=True)

    @api.depends('product_manufacture_step_ids', 'product_manufacture_step_ids.bom_id', 'product_manufacture_step_ids.routing_id')
    def _compute_manufacturing_steps_operation(self):
        """ Retrieve all manufacturing steps operations (BoMs and routes used) """
        for line in self:
            line.route_ids = line.product_manufacture_step_ids.mapped('routing_id')
            line.bom_ids = line.product_manufacture_step_ids.mapped('bom_id')

    @api.depends('product_manufacture_step_ids', 'product_manufacture_step_ids.bom_id', 'product_manufacture_step_ids.bom_id.bom_line_ids')
    def _compute_raw_product_ids(self):
        """ Retrieve BoM components from first step (step with the greatest sequence) """
        for line in self:
            sorted_steps = line.product_manufacture_step_ids.filtered(lambda step: step.bom_id and step.bom_id.bom_line_ids).sorted(key=lambda step: step.sequence)
            if sorted_steps:
                if len(sorted_steps) > 1:
                    line.raw_product_ids = sorted_steps[-1].bom_id.bom_line_ids.mapped('product_id')
                else:
                    line.raw_product_ids = sorted_steps.bom_id.bom_line_ids.mapped('product_id')
            else:
                line.raw_product_ids = False

    @api.depends('product_manufacture_step_ids',
                 'product_manufacture_step_ids.bom_id',
                 'product_manufacture_step_ids.bom_id.mothersheet_length',
                 'product_manufacture_step_ids.bom_id.mothersheet_width')
    def _compute_mothersheet_size(self):
        """ Retrieve mothersheet size from first step (step with the greatest sequence) that produces mothersheet """
        for line in self:
            length = 0.0
            width = 0.0
            sorted_steps = line.product_manufacture_step_ids.sorted(key=lambda step: step.sequence, reverse=True)
            for step in sorted_steps:
                if step.bom_id and step.bom_id.does_produce_mothersheet:
                    length = step.bom_id.mothersheet_length
                    width = step.bom_id.mothersheet_width
                    break
            line.write({'mothersheet_length': length, 'mothersheet_width': width})

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
            if line.purchase_price > 0.0:
                self.calculate_product_cost_action()

    def action_cost_analysis(self):
        """ Open report view of all done MO linked to sale order line """
        self.ensure_one()
        productions = self.product_manufacture_step_ids.mapped('production_id').filtered(lambda prod: prod.state == 'done')
        return self.env.ref('mrp_account_enterprise.action_cost_struct_mrp_production').report_action(productions, config=False)

    @api.depends('product_manufacture_step_ids.bom_id.product_qty', 'product_manufacture_step_ids.bom_efficiency',
                 'product_manufacture_step_ids.bom_id.bom_line_ids', 'product_manufacture_step_ids.product_id',
                 'product_manufacture_step_ids.sequence', 'finished_product_quantity', 'product_uom_qty', 'configuration_is_done')
    def _compute_max_producible_qty(self):
        """ Compute the maximum producible quantity"""
        for line in self:
            line.max_producible_quantity = 0
            if line.configuration_is_done:
                max_product_qty = line.get_max_product_qty()
                if max_product_qty:
                    line.max_producible_quantity = max_product_qty[1]['qty_to_produce']

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        so_line_mo_qty = {}
        for line in self:
            so_line_mo_qty[line.id] = line.get_max_product_qty()
        return super(AGCSaleOrderLine, self.with_context(mo_qty=so_line_mo_qty))._action_launch_stock_rule(previous_product_uom_qty=previous_product_uom_qty)

    def get_max_product_qty(self):
        """Compute the min qty needed and the maximum producible quantity for each MO"""
        self.ensure_one()
        mo_qty = dict()
        for step in self.product_manufacture_step_ids:
            if step.sequence == 1:
                qty_needed = self.product_uom_qty
                factor = ceil(qty_needed / self.finished_product_quantity)
                factor = factor / (step.bom_id.product_qty or 1.0)
                factor = ceil(factor * (100 / step.bom_efficiency))
                qty_to_produce = factor * step.bom_id.product_qty * self.finished_product_quantity
            else:
                qty_needed = mo_qty[step.sequence - 1]['raw_mat'][step.product_id.id]['qty_needed']
                factor = qty_needed / (step.bom_id.product_qty or 1.0)
                factor = ceil(factor * (100 / step.bom_efficiency))
                qty_to_produce = factor * step.bom_id.product_qty

            mo_qty.update({
                step.sequence: {
                    'qty_needed': qty_needed,
                    'qty_to_produce': qty_to_produce,
                    'product_id': step.product_id.id,
                    'factor': factor,
                    'raw_mat': dict()}})

            for raw_line in step.bom_id.bom_line_ids:
                mo_qty[step.sequence]['raw_mat'].update({raw_line.product_id.id: {
                    'qty_needed': raw_line.product_qty * factor,
                    'bom_qty': raw_line.product_qty}})
        if mo_qty:
            i = max(mo_qty.keys()) - 1
            while i > 0:
                max_raw_mat_produced = mo_qty[i + 1]['qty_to_produce']
                raw_mat_product_id = mo_qty[i + 1]['product_id']
                raw_mat_bom_qty = mo_qty[i]['raw_mat'][raw_mat_product_id]['bom_qty']
                factor = ceil(max_raw_mat_produced / raw_mat_bom_qty)
                mo_qty[i]['qty_to_produce'] = (mo_qty[i]['qty_to_produce'] / mo_qty[i]['factor']) * factor
                mo_qty[i]['max_factor'] = factor
                i -= 1
        return mo_qty

    def open_fp_configuration_view(self):
        """
        Return a different view depending on whether the SO is confirmed or not
        """
        self.ensure_one()
        if self.state not in ('sale', 'done', 'cancel'):
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
                    raise ValidationError(_('the BOM {} is not of type subcontract').format(step_line.bom_id.name_get()))
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
        self.purchase_price = 0.0
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
                self.purchase_price = sorted_steps[-1].price_unit / (self.finished_product_quantity or 1)
            return self.open_fp_configuration_view()
