# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    warning_message = fields.Text(string='comment', compute='_compute_warning_message', store=True)

    @api.depends('mo_id.product_qty', 'workorder_id.qty_producing')
    def _compute_warning_message(self):
        for wizard in self:
            qty_producing = wizard.workorder_id.qty_producing
            qty_to_produce = wizard.mo_id.product_qty
            quantities_message = ''
            if float_compare(qty_producing, qty_to_produce, precision_digits=2) > 0:
                quantities_message = (_('You are about to produce more quantities than expected (producing quantity: {}, quantity expected to produce: {}).\n')).format(qty_producing, qty_to_produce)
            elif float_compare(qty_producing, qty_to_produce, precision_digits=2) < 0:
                quantities_message = (_('You are about to produce less quantities than expected (producing quantity: {}, quantity expected to produce: {}).\n')).format(qty_producing, qty_to_produce)
            wizard.warning_message = '{}{}'.format(quantities_message, _('Validate only if you are sure of what you are doing. You won\'t be able to produce more or less quantities afterwards.'))

    def change_prod_qty_and_validate(self):
        self.ensure_one()
        if self.workorder_id:
            self.change_prod_qty()
            return self.workorder_id.action_next()
        else:
            return False

    def change_prod_qty(self):
        """ overridden method
        Add context used to retrieve production in mrp.bom explode() method """
        self.ensure_one()
        self = self.with_context(production_id=self.mo_id.id)
        return super(ChangeProductionQty, self).change_prod_qty()