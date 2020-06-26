# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCRoutingEfficiency(models.Model):
    _name = 'mrp.routing.efficiency'
    _description = "Record associating a routing's complexity to an efficiency in percent."

    name = fields.Char(string='Complexity Name', size=64, translate=True, required=True)
    efficiency = fields.Integer(string='Yield (%)', default=100, help='This parameter allows to adapt Routing efficiency, its value must be inluded between 0 and 100.\n'
                                                                      'If it is lower than 100 it will impact the cost evaluation of the manufacturing process.\n')

    @api.constrains('efficiency')
    def _check_efficiency_domain(self):
        """
        Make sure that efficiency is in teh range ]0; 100]
        """
        for routing_efficiency in self:
            if not 0 < routing_efficiency.efficiency <= 100:
                raise UserError(_('The Yield must be greater than 0 and lower or equal than 100.'))
