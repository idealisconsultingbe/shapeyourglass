# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCBom(models.Model):
    _inherit = 'mrp.bom'

    efficiency = fields.Integer(string='Yield (%)', default=100, help='This parameter allows to adapt the efficiency of the BoM, its value must be included between 0 and 100.'
                                                                      'If it is lower than 100 it will impact cost evaluation of the manufacturing process.'
                                                                      'It will also impact the quantity of raw material send to the manufacturing location.')
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
