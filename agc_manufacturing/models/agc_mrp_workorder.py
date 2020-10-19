# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AGCMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    finished_lot_id = fields.Many2one('stock.production.lot', readonly=True)

