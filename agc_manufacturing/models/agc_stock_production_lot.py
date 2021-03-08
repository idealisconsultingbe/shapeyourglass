# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AgcProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    name = fields.Char(string='Lot/Serial Number', readonly=True)
    ref = fields.Char(string='Internal Reference', compute='_compute_ref', store=True)
    stock_move_line_ids = fields.One2many('stock.move.line', 'lot_id', string='Stock Move Lines')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    unit_cost = fields.Monetary(currency_field='currency_id', string='Unit Cost', default=0.0)
    value_cost = fields.Monetary(currency_field='currency_id', string='Value Cost', compute='_compute_value_cost', store=True, readonly=True)

    length = fields.Float(string='Product Length (mm)', compute='_compute_product_size', store=True)
    width = fields.Float(string='Product Width (mm)', compute='_compute_product_size', store=True)

    @api.depends('stock_move_line_ids.move_id.sale_order_line_id',
                 'stock_move_line_ids.move_id.sale_order_line_id.width',
                 'stock_move_line_ids.move_id.sale_order_line_id.length',
                 'stock_move_line_ids.move_id.sale_order_line_id.mothersheet_width',
                 'stock_move_line_ids.move_id.sale_order_line_id.mothersheet_length')
    def _compute_product_size(self):
        """
        Retrieve product size from sale order line
        If lot product is a mothersheet (intermediate product in manufacturing steps), then retrieve mothersheet size
        If lot product is a final product, then retrieve product size
        """
        for lot in self:
            length = 0.0
            width = 0.0
            if lot.stock_move_line_ids:
                moves = lot.stock_move_line_ids.mapped('move_id')
                order_lines = moves.mapped('sale_order_line_id') if moves else False
                if order_lines:
                    order_lines = order_lines.filtered(lambda line: line.product_manufacture_step_ids)
                    for candidate_line in order_lines:
                        if candidate_line.product_id == lot.product_id:
                            length = candidate_line.length
                            width = candidate_line.width
                            break
                        elif lot.product_id in candidate_line.product_manufacture_step_ids.mapped('product_id'):
                            length = candidate_line.mothersheet_length
                            width = candidate_line.mothersheet_width
                            break
            lot.write({'length': length, 'width': width})

    @api.depends('stock_move_line_ids.produce_line_ids', 'stock_move_line_ids.consume_line_ids')
    def _compute_ref(self):
        """
        If lot is linked to a mrp.production the internal reference of the lot contains BOM and routing details
        """
        for lot in self:
            lot.ref = lot.get_lot_generated_ref()

    @api.depends('product_qty', 'unit_cost')
    def _compute_value_cost(self):
        """
        Cost value is computed here and stored in database depending on lot quantity and unit cost
        """
        for lot in self:
            lot.value_cost = lot.product_qty*lot.unit_cost

    def get_previous_move_line(self, line):
        """
        A move can have been generated by a consumption or can be preceded by an older move.
        :line: A stock move line
        :return: The move that precede the stock move line given in parameter
        """
        traceability_model = self.env['stock.traceability.report']
        consumed_line = traceability_model._get_linked_move_lines(line)[0]
        previous_move_line = traceability_model._get_move_lines(line)
        return consumed_line or previous_move_line

    def get_initial_move_line(self, line):
        """
        :param line: A stock move line
        :return: Find the stock move line that is at the origin of the line given in parameters
        """
        initial_line = line
        while(self.get_previous_move_line(initial_line)):
            child_lines = self.get_previous_move_line(initial_line).sorted(lambda move_line: move_line.date)
            initial_line = child_lines[0]
        return initial_line

    def get_lot_generated_ref(self):
        """
        :return: A string with details of the object that has initially generated this lot.
        """
        self.ensure_one()
        generated_reference = ""
        line = self.stock_move_line_ids.sorted(lambda move_line: move_line.date)
        if line:
            line = line[0]
            initial_move = self.get_initial_move_line(line)
            res_model, res_id, ref = self.env['stock.traceability.report']._get_reference(line)
            if res_model == 'mrp.production':
                mrp_production = self.env[res_model].browse(res_id)
                does_produce_mothersheet = mrp_production.bom_id.does_produce_mothersheet
                bom_code = mrp_production.bom_id.code
                routing_name = mrp_production.routing_id.name_get()[0][1] if mrp_production.routing_id else ''
                ms_length = int(mrp_production.bom_id.mothersheet_length)
                ms_width = int(mrp_production.bom_id.mothersheet_width)
                ms_size = "[L{}xW{}]".format(ms_length, ms_width)
                generated_reference = "[{}{} + {}]".format(ms_size if does_produce_mothersheet else '', bom_code, routing_name)
            else:
                generated_reference = "[{}]".format(initial_move.product_id.name_get()[0][1])
        return generated_reference
