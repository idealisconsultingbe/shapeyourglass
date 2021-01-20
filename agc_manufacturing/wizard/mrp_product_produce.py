# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def button_close_mo(self):
        self.ensure_one()
        if any(self.raw_workorder_line_ids.mapped('qty_done')):
            self.do_produce()
        self.production_id.write({'state': 'to_close'})
