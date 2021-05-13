# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LocationRoute(models.Model):
    _inherit = 'stock.location.route'

    no_config_needed = fields.Boolean(string='No Manufacturing Steps Configuration', help='Used on sale order lines to avoid configuration of manufacturing steps. '
                                                                                          'However, It is still possible to change this directly on sale order lines.')
