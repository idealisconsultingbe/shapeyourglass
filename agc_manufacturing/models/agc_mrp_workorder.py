# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AGCMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    finished_lot_id = fields.Many2one('stock.production.lot', readonly=True)
    qty_needed = fields.Float(string='Min Quantity To Produce', related='production_id.qty_needed', help="Minimum quantity to produce in order to reach the quantity ordered by the customer.")
    state = fields.Selection(selection_add=[('waiting', 'Waiting for Components'), ('ready',)])
    order_blocked_message = fields.Text(string='Order Blocked Message', compute='_compute_order_blocked_message')

    @api.depends('state')
    def _compute_order_blocked_message(self):
        """ Compute message of a 'waiting for components' workorder """
        for order in self:
            order.order_blocked_message = ''
            if order.state == 'waiting':
                order.order_blocked_message = _('There are components without any reserved quantities ({}). Please check availability of those components before processing production.')\
                        .format(', '.join(order.raw_workorder_line_ids.filtered(lambda l: not l.qty_reserved).mapped('product_id.name')))

    def _refresh_wo_lines(self):
        """
        Overridden method
        When refreshing WO lines, set workorder state to ready if all lines have reserved quantities
        """
        super(AGCMrpWorkorder, self)._refresh_wo_lines()
        for workorder in self.filtered(lambda w: w.state != 'done'):
            if all(workorder.move_raw_ids.mapped('reserved_availability')):
                workorder.state = 'ready'

    def name_get(self):
        """ Overwritten method in order to add production SO name to display name """
        return [(wo.id, "{} - {} - {}".format(wo.production_id.sale_order_id and '{} - {}'
                                              .format(wo.production_id.name, wo.production_id.sale_order_id.name)
                                              or wo.production_id.name, wo.product_id.name, wo.name)) for wo in self]

    def record_production(self):
        """
        Overridden method
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
        """
        Overridden method
        Set working state to 'blocked' if there are components without reserved quantities.
        This prevents order to be started automatically
        """
        self.ensure_one()
        self.working_state = self.workcenter_id.working_state
        if self.state == 'waiting':
            self.working_state = 'blocked'
        return super(AGCMrpWorkorder, self).open_tablet_view()

    def action_assign(self):
        """ Same method as the 'check availability' method on MO """
        self.ensure_one()
        self.production_id.move_raw_ids._action_assign()
        self.production_id.workorder_ids._refresh_wo_lines()
        return True
