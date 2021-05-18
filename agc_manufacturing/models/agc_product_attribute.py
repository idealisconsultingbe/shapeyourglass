# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AGCProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_a_dimension = fields.Boolean(string='Is a Dimension Attribute')
    dimension_type = fields.Selection([('thickness', 'Thickness'), ('width', 'Width'), ('length', 'Length')], string='Dimension Type')

    @api.constrains('dimension_type')
    def _check_dimension_type(self):
        for record in self:
            if record.is_a_dimension and not record.dimension_type:
                raise UserError(_('A dimension attribute should have a type of dimension (see product attribute: {})').format(record.name))