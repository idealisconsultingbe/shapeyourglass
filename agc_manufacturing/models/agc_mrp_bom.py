# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCBom(models.Model):
    _inherit = 'mrp.bom'

    does_produce_mothersheet = fields.Boolean(string='Mothersheet', default=False, help='Flag this option if this bom consume DLS and produce mothersheet.')
    mothersheet_length = fields.Float(string='Mothersheet Length (mm)', default=0.0)
    mothersheet_width = fields.Float(string='Mothersheet Width (mm)', default=0.0)
    product_id = fields.Many2one('product.product', required=True)

    @api.constrains('efficiency')
    def _check_efficiency_domain(self):
        """
        Make sure that efficiency is in the range ]0; 100].
        """
        for bom in self:
            if not 0 < bom.efficiency <= 100:
                raise UserError(_('The Yield must be greater than 0 and lower or equal than 100.'))
