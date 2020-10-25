# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AGCMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    finished_lot_id = fields.Many2one('stock.production.lot', readonly=True)
    qty_needed = fields.Float(string='Min Quantity To Produce', related='production_id.qty_needed', help="Minimum quantity to produce in order to reach the quantity ordered by the customer.")

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
