# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AGCMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    finished_lot_id = fields.Many2one('stock.production.lot', readonly=True)
    qty_needed = fields.Float(string='Min Quantity To Produce', related='production_id.qty_needed', help="Minimum quantity to produce in order to reach the quantity ordered by the customer.")
    order_blocked = fields.Boolean(string='Order Blocked', compute='_compute_order_blocked', help='Block order if at least one component has none quantity reserved')

    @api.depends('production_id.move_raw_ids.state',
                 'production_id.move_finished_ids.state',
                 'production_id.workorder_ids',
                 'production_id.workorder_ids.state',
                 'production_id.qty_produced',
                 'production_id.move_raw_ids.quantity_done',
                 'production_id.product_qty')
    def _compute_order_blocked(self):
        for order in self:
            order.order_blocked = False
            if order.production_id.move_raw_ids._get_relevant_state_among_moves() in ['waiting', 'partially_available']:
                if any(order.production_id.move_raw_ids.filtered(lambda m: not m.reserved_availability)):
                    order.order_blocked = True

    def name_get(self):
        """ Overwritten method in order to add production SO to display name """
        return [(wo.id, "{} - {} - {}".format(wo.production_id.sale_order_id and '{} - {}'
                                              .format(wo.production_id.name, wo.production_id.sale_order_id.name)
                                              or wo.production_id.name, wo.product_id.name, wo.name)) for wo in self]

    def record_production(self):
        """
        In case we interrupt a production before the end we do not record production for the current step that has not been validated.
        """
        if self.env.context.get('interrupt_production', False):
            return True
        else:
            return super(AGCMrpWorkorder, self).record_production()

    def stop_production_and_close_mo(self):
        """
        Allow to stop a production in progress before reaching the planned quantity.
        """
        # Delete the quality check for the current step.
        qc_to_delete = self.check_ids.filtered(lambda qc: qc.quality_state != 'pass')
        qc_to_delete.unlink()
        self.button_finish()
        return self.with_context(interrupt_production=True).action_open_manufacturing_order()

    def open_tablet_view(self):
        self.ensure_one()
        self.working_state = self.workcenter_id.working_state
        if self.order_blocked:
            self.working_state = 'blocked'
        return super(AGCMrpWorkorder, self).open_tablet_view()
