# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AGCProduction(models.Model):
    _inherit = "mrp.production"

    routing_id = fields.Many2one('mrp.routing', string='Routing', readonly=True, compute=False,
                                 states={'draft': [('readonly', False)]},
                                 required=True, domain="""[
                                         '&',
                                            '|',
                                                ('company_id', '=', False),
                                                ('company_id', '=', company_id),
                                                '|',
                                                    ('product_id','=',product_id),
                                                    ('product_id','=',False)]""", check_company=True)


    def _generate_workorders(self, exploded_boms):
        """ Overriden method

        Standard method uses routing from BoM while we want to use routing from production.
        Changes were only made to conditions to reflect this new behaviour
        """
        workorders = self.env['mrp.workorder']
        original_one = False
        for bom, bom_data in exploded_boms:
            # Changes from standard
            if self.routing_id.id and (not bom_data['parent_line'] or bom_data[
                                        'parent_line'].bom_id.routing_id.id != self.routing_id.id):
                # end of changes
                temp_workorders = self._workorders_create(bom, bom_data)
                workorders += temp_workorders
                if temp_workorders:  # In order to avoid two "ending work orders"
                    if original_one:
                        temp_workorders[-1].next_work_order_id = original_one
                    original_one = temp_workorders[0]
        return workorders

    def _workorders_create(self, bom, bom_data):
        """ Overriden method

        Standard method uses routing from BoM while we want to use routing from production.
        Changes were made to workorder creation, and raw moves to reflect this new behaviour
        """
        workorders = self.env['mrp.workorder']

        # Initial qty producing
        quantity = max(self.product_qty - sum(self.move_finished_ids.filtered(lambda move: move.product_id == self.product_id).mapped('quantity_done')), 0)
        quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom_id)
        if self.product_id.tracking == 'serial':
            quantity = 1.0

        # Changes from standard
        for operation in self.routing_id.operation_ids:
            # end of changes
            workorder = workorders.create({
                'name': operation.name,
                'production_id': self.id,
                'workcenter_id': operation.workcenter_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'operation_id': operation.id,
                'state': len(workorders) == 0 and 'ready' or 'pending',
                'qty_producing': quantity,
                'consumption': self.bom_id.consumption,
            })
            if workorders:
                workorders[-1].next_work_order_id = workorder.id
                workorders[-1]._start_nextworkorder()
            workorders += workorder

            # Changes from standard
            moves_raw = self.move_raw_ids.filtered(lambda move: move.operation_id == operation and move.production_id.routing_id == self.routing_id)
            # end of changes

            moves_finished = self.move_finished_ids.filtered(lambda move: move.operation_id == operation)


            # Changes from standard
            if len(workorders) == len(self.routing_id.operation_ids):
                moves_raw |= self.move_raw_ids.filtered(lambda move: not move.operation_id and move.production_id.routing_id == self.routing_id)
                moves_raw |= self.move_raw_ids.filtered(lambda move: not move.workorder_id and not move.production_id.routing_id)
                # end of changes

                moves_finished |= self.move_finished_ids.filtered(lambda move: move.product_id != self.product_id and not move.operation_id)

            moves_raw.mapped('move_line_ids').write({'workorder_id': workorder.id})
            (moves_finished | moves_raw).write({'workorder_id': workorder.id})

            workorder._generate_wo_lines()
        return workorders

    def _cal_price(self, consumed_moves):
        """
        The standard method has been overriden in order to compute the unit cost of a lot
        """
        res =  super(AGCProduction, self)._cal_price(consumed_moves)
        work_center_cost = 0
        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            for work_order in self.workorder_ids:
                time_lines = work_order.time_ids.filtered(lambda x: x.date_end and not x.cost_already_recorded)
                duration = sum(time_lines.mapped('duration'))
                time_lines.write({'cost_already_recorded': True})
                work_center_cost += (duration / 60.0) * work_order.workcenter_id.costs_hour
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                qty_done = finished_move.product_uom._compute_quantity(finished_move.quantity_done,
                                                                       finished_move.product_id.uom_id)
                extra_cost = self.extra_cost * qty_done
                finished_move.price_unit = (sum([-m.stock_valuation_layer_ids.value for m in
                                                 consumed_moves.sudo()]) + work_center_cost + extra_cost) / qty_done
                for line in finished_move.move_line_ids:
                    if line.lot_id:
                        line.lot_id.unit_cost = finished_move.price_unit
        return res
