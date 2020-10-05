# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class AGCMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    finished_lot_id = fields.Many2one('stock.production.lot', readonly=True)

    def action_force_open_manufacturing_order(self):
        """
        Mix of record_production() and action_open_manufacturing_order() methods
        in order to finish workorder before producing all quantities
        """
        # --------------------------
        # Record_production() logic
        # --------------------------
        if not self:
            return True

        self.ensure_one()
        self._check_company()
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

        # If last work order, then post lots used
        if not self.next_work_order_id:
            self._update_finished_move()

        # Transfer quantities from temporary to final move line or make them final
        self._update_moves()

        # Transfer lot (if present) and quantity produced to a finished workorder line
        if self.product_tracking != 'none':
            self._create_or_update_finished_line()

        # Update workorder quantity produced
        self.qty_produced += self.qty_producing

        # Suggest a finished lot on the next workorder
        if self.next_work_order_id and self.product_tracking != 'none' and (not self.next_work_order_id.finished_lot_id or self.next_work_order_id.finished_lot_id == self.finished_lot_id):
            self.next_work_order_id._defaults_from_finished_workorder_line(self.finished_workorder_line_ids)
            # As we may have changed the quantity to produce on the next workorder,
            # make sure to update its wokorder lines
            self.next_work_order_id._apply_update_workorder_lines()

        # One a piece is produced, you can launch the next work order
        self._start_nextworkorder()

        # Changes to record_production() here
        # finish production even if production is not done
        self.qty_producing = 0
        self.button_finish()
        # end of changes

        # ----------------------------------------------------
        # action_open_manufacturing_order() logic
        # ----------------------------------------------------
        # Changes here
        action = self.force_do_finish()
        # end of changes
        try:
            self.production_id.button_mark_done()
        except (UserError, ValidationError) as e:
            # log next activity on MO with error message
            self.env['mail.activity'].create({
                'res_id': self.production_id.id,
                'res_model_id': self.env['ir.model']._get(self.production_id._name).id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                'summary': ('The %s could not be closed') % (self.production_id.name),
                'note': e.name,
                'user_id': self.env.user.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.production_id.id,
                'target': 'main',
            }
        return action

    def force_do_finish(self):
        """
        Inspired by do_finish() method which triggers record_production() method and switches to workorders kanban or tree view
        Since record_production() has already been triggered, this part is skipped
        """
        # workorder tree view action should redirect to the same view instead of workorder kanban view when WO mark as done.
        if self.env.context.get('active_model') == self._name:
            action = self.env.ref('mrp.action_mrp_workorder_production_specific').read()[0]
            action['context'] = {'search_default_production_id': self.production_id.id}
            action['target'] = 'main'
        else:
            # workorder tablet view action should redirect to the same tablet view with same workcenter when WO mark as done.
            action = self.env.ref('mrp_workorder.mrp_workorder_action_tablet').read()[0]
            action['context'] = {
                'form_view_initial_mode': 'edit',
                'no_breadcrumbs': True,
                'search_default_workcenter_id': self.workcenter_id.id
            }
        action['domain'] = [('state', 'not in', ['done', 'cancel', 'pending'])]
        return action
