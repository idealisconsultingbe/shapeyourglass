# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AGCBom(models.Model):
    _inherit = 'mrp.bom'

    efficiency = fields.Integer(string='Yield (%)', default=100)
    mothersheet_length = fields.Float(string='Mothersheet Length (mm)', default=0.0)
    mothersheet_width = fields.Float(string='Mothersheet Width (mm)', default=0.0)

    @api.constrains('efficiency')
    def efficiency_domain(self):
        """
        Make sure that the efficiency is in the range ]0; 100]
        """
        for bom in self:
            if not 0 < bom.efficiency <= 100:
                raise UserError(_('The Yield must be greater than 0 or lower/equal to 100.'))