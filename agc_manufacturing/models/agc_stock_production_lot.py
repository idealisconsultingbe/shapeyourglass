# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AgcProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    name = fields.Char(string='Lot/Serial Number', readonly=True)
    ref = fields.Char(string='Internal Reference', compute='_get_internal_reference', store=True)
    stock_move_line_ids = fields.One2many('stock.move.line', 'lot_id', string='Stock Move Lines')

    def get_previous_move(self, line):
        """
        A move can have been generated by a consumption or can be preceded by an older move.
        :line: A stock move line
        :return: The move that precede the stock move line given in parameter
        """
        traceability_model = self.env['stock.traceability.report']
        consumed_line = traceability_model._get_linked_move_lines(line)[0]
        previous_move_line = traceability_model._get_move_lines(line)
        return consumed_line or previous_move_line

    def get_initial_move(self, line):
        """
        :param line: A stock move line
        :return: Find the stock move line that is at origin of the line given in parameters
        """
        current_line = line
        while(self.get_previous_move(current_line)):
            child_lines = self.get_previous_move(current_line).sorted(lambda move_line: move_line.date)
            current_line = child_lines[0]
        return current_line

    def get_lot_generated_ref(self):
        """
        :return: A string with details of the object that has initially generated this lot.
        """
        self.ensure_one()
        generated_reference = ""
        line = self.stock_move_line_ids.sorted(lambda move_line: move_line.date)
        if line:
            line = line[0]
            initial_move = self.get_initial_move(line)
            res_model, res_id, ref = self.env['stock.traceability.report']._get_reference(line)
            if res_model == 'mrp.production':
                mrp_production = self.env[res_model].browse(res_id)
                generated_reference = "[{}: {} + {}]".format(initial_move.product_id.name_get()[0][1],
                                                             mrp_production.bom_id.name_get()[0][1],
                                                             mrp_production.routing_id.name_get()[0][1] if mrp_production.routing_id else '')
            else:
                generated_reference = "[{}]".format(initial_move.product_id.name_get()[0][1])
        return generated_reference

    @api.depends('stock_move_line_ids.produce_line_ids', 'stock_move_line_ids.consume_line_ids')
    def _get_internal_reference(self):
        """
        If the lot is linked to an mrp.production the internal reference of the lot contains the bom and routing details
        """
        for lot in self:
            lot.ref = lot.get_lot_generated_ref()
