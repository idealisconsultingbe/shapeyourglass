# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AGCRoutingEfficiency(models.Model):
    _name = 'mrp.routing.efficiency'
    _description = "Record associating a routing's complexity to an efficiency in percent."

    name = fields.Char(string='Complexity Name', size=64, translate=True, required=True)
    efficiency = fields.Integer(string='Yield (%)', default=100, help='This parameter allows to adapt the efficiency of the Routing, its value must be comprised between 0 and 100.'
                                                                      'If it is lower than 100 it will impact the evaluation of the cost of the manufacturing process.'
                                                                      'It will also impact the quantity of raw material send to the manufacturing location.')

    @api.constrains('efficiency')
    def efficiency_domain(self):
        """
        Make sure that the efficiency is in the range ]0; 100]
        """
        for routing_efficiency in self:
            if not 0 < routing_efficiency.efficiency <= 100:
                raise UserError(_('The Yield must be greater than 0 and lower or equal than 100.'))
