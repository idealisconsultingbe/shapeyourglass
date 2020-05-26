# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AGCRoutingEfficiency(models.Model):
    _name = 'mrp.routing.efficiency'
    _description = "Record associating a routing's complexity to an efficiency in percent."

    name = fields.Char(string='Complexity Name', translate=True, required=True)
    efficiency = fields.Integer(string='Yield (%)', default=100)

    @api.constrains('efficiency')
    def efficiency_domain(self):
        """
        Make sure that the efficiency is in the range ]0; 100]
        """
        for routing_efficiency in self:
            if not 0 < routing_efficiency.efficiency <= 100:
                raise UserError(_('The Yield must be greater than 0 or lower/equal to 100.'))
