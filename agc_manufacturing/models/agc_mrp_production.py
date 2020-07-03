# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from math import ceil


class AGCProduction(models.Model):
    _inherit = 'mrp.production'

    product_manufacture_step_ids = fields.One2many('product.manufacturing.step', 'production_id', string='Finished Product Manufacturing Step')
    subcontract_move_dest_id = fields.Many2one('stock.move', string='Subcontract Destination', help='Technical field used to find easily from which move comes the subcontracted demand.')
    routing_id = fields.Many2one('mrp.routing', string='Routing', readonly=True, compute=False, required=True,
                                 states={'draft': [('readonly', False)]},
                                 domain="""[
                                 '&',
                                    '|',
                                        ('company_id', '=', False),
                                        ('company_id', '=', company_id),
                                        '|',
                                            ('product_id','=',product_id),
                                            ('product_id','=',False)]""", check_company=True)

    @api.constrains('product_manufacture_step_ids')
    def _check_product_manufacture_step_one2one(self):
        """
        The link between an MO and its product manufacturing step should be a one2one.
        Make sure that no more than one product manufacturing step is linked to an MO.
        """
        for production in self:
            if len(production.product_manufacture_step_ids or []) > 1:
                raise UserError(_('MO should not have more than one Finished Product Manufacturing Step. See MO({})').format(production.name))

    def _get_moves_raw_values(self):
        """ Overridden method

        Changes to factor computation of finished product configuration to take into account the number of products per mothersheet
        """
        if self.env.context.get('pf_configure', False):
            moves = []
            for production in self:

                if production.product_id.categ_id.product_type == 'finished_product' and production.product_manufacture_step_ids:
                    so_line_uom = production.product_manufacture_step_ids.sale_line_id.product_uom
                    qty_needed = so_line_uom._compute_quantity(
                        production.product_manufacture_step_ids.sale_line_id.product_uom_qty,
                        production.bom_id.product_uom_id)
                    product_per_ms = production.product_manufacture_step_ids.sale_line_id.finished_product_quantity
                    factor = ceil(qty_needed / product_per_ms) / production.bom_id.product_qty
                else:
                    factor = production.product_uom_id._compute_quantity(production.product_qty,
                                                                         production.bom_id.product_uom_id) / production.bom_id.product_qty
                bom_efficiency = production.product_manufacture_step_ids.bom_efficiency / 100 or 1
                factor = factor / bom_efficiency
                boms, lines = production.bom_id.explode(production.product_id, factor,
                                                        picking_type=production.bom_id.picking_type_id)
                for bom_line, line_data in lines:
                    if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or \
                            bom_line.product_id.type not in ['product', 'consu']:
                        continue
                    moves.append(production._get_move_raw_values(bom_line, line_data))
            return moves
        else:
            return super(AGCProduction, self)._get_moves_raw_values()

    def _generate_workorders(self, exploded_boms):
        """ Overridden method

        Standard method uses routing from BoM while we want to use routing from manufacturing order.
        """
        workorders = self.env['mrp.workorder']
        original_one = False
        for bom, bom_data in exploded_boms:
            # Changes from standard
            if self.routing_id.id and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.routing_id.id != self.routing_id.id):
                # end of changes
                temp_workorders = self._workorders_create(bom, bom_data)
                workorders += temp_workorders
                if temp_workorders:  # In order to avoid two "ending work orders"
                    if original_one:
                        temp_workorders[-1].next_work_order_id = original_one
                    original_one = temp_workorders[0]
        return workorders

    def _workorders_create(self, bom, bom_data):
        """ Overridden method

        Standard method uses routing from BoM while we want to use routing from manufacturing order.
        Changes were made on workorder creation, and on raw moves to reflect this new behaviour
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
        Override standard method in order to compute lot unit cost
        """
        res =  super(AGCProduction, self)._cal_price(consumed_moves)
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        if finished_move:
            finished_move.ensure_one()
            if finished_move.product_id.cost_method in ('fifo', 'average'):
                for line in finished_move.move_line_ids:
                    if line.lot_id:
                        line.lot_id.unit_cost = finished_move.product_uom._compute_price(finished_move.price_unit, line.lot_id.product_uom_id)
        return res
