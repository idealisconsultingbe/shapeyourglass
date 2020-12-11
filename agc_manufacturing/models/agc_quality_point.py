# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class QualityPoint(models.Model):
    _inherit = "quality.point"

    @api.onchange('product_id', 'product_tmpl_id', 'picking_type_id', 'test_type_id')
    def _onchange_product(self):
        """
        Overwrite standard method
        Routing are not mandatory anymore on the bom
        Routing are directly linked to product variant
        We adapt domain bas on those changes
        """
        bom_ids = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)])
        component_ids = set([])
        if self.test_type == 'register_consumed_materials':
            for bom in bom_ids:
                boms_done, lines_done = bom.explode(self.product_id, 1.0)
                component_ids |= {l[0].product_id.id for l in lines_done}
        if self.test_type == 'register_byproducts':
            for bom in bom_ids:
                component_ids |= {byproduct.product_id.id for byproduct in bom.byproduct_ids}
        # Custom changes start here
        all_routings = self.env['mrp.routing'].search([])
        allow_products = all_routings.mapped('product_id')
        allow_product_templates = allow_products.mapped('product_tmpl_id')
        routing_ids = self.env['mrp.routing'].search([('product_id', '=', self.product_id.id)]).ids
        if self.picking_type_id.code == 'mrp_operation':
            return {
                'domain': {
                    'operation_id': [('routing_id', 'in', routing_ids), '|', ('company_id', '=', self.company_id.id),
                                     ('company_id', '=', False)],
                    'component_id': [('id', 'in', list(component_ids)), '|', ('company_id', '=', self.company_id.id),
                                     ('company_id', '=', False)],
                    'product_tmpl_id': [('bom_ids', '!=', False), ('id', 'in', allow_product_templates.ids), '|',
                                        ('company_id', '=', self.company_id.id), ('company_id', '=', False)],
                    'product_id': [('variant_bom_ids', '!=', False), ('id', 'in', allow_products.ids), '|',
                                   ('company_id', '=', self.company_id.id), ('company_id', '=', False)],
                }
            }
        # Custom changes end here