# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AGCProductManufacturingStep(models.Model):
    _name = 'product.manufacturing.step'
    _description = 'Each record describes a step of the manufacturing chain aiming to produced a finished product.'
    _order = 'sequence'

    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', required=True, ondelete='cascade')
    configuration_is_done = fields.Boolean(related='sale_line_id.configuration_is_done', string='Finished Product Configuration is Done', help='Technical field that helps to know whether the Finished Product configuration is done.')
    sale_order_state = fields.Selection(related='sale_line_id.order_id.state', string='Sale Order Status')
    sequence = fields.Integer(string='Sequence', help="Used to order the 'Product Manufacturing Step' tree view", default=1)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', domain="[('product_id', '=', product_id), ('active', '=', True)]")
    bom_type = fields.Selection(related='bom_id.type', string='BoM Type')
    initial_bom_efficiency = fields.Integer(string='Initial BoM  Yield (%)', compute='_get_initial_bom_yield')
    bom_efficiency = fields.Integer(string='BoM  Yield (%)', default=100, help='This parameter allows to adapt BOM efficiency. Its value must be lower or equal to 100 and higher than zero.\n'
                                                                               'A value lower than 100 will impact the cost evaluation of the manufacturing process.\n'
                                                                               'It will also impact the quantity of raw materials send to the manufacturing location.\n')
    routing_id = fields.Many2one('mrp.routing', string='Routing', domain="[('product_id', '=', product_id), ('active', '=', True)]")
    routing_efficiency_id = fields.Many2one('mrp.routing.efficiency', string='Routing Complexity', help='This parameter allows to adapt Routing efficiency, its value must be included between 0 and 100.\n'
                                                                                                        'If the complexity as an efficiency lower than 100 it will impact the cost evaluation of the manufacturing process.\n')
    currency_id = fields.Many2one('res.currency', related='sale_line_id.currency_id', string='Currency')
    price_unit = fields.Monetary(string='Unit Cost', default='0.0')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    production_status = fields.Selection(related='production_id.state', string='MO Status', help='Display the status of the Manufacturing Order')
    production_date = fields.Datetime(related='production_id.date_planned_finished', srting='MO Finished Date', help='Date at which you planned to finish the production')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    purchase_id = fields.Many2one('purchase.order', related='purchase_line_id.order_id', string='Purchase Order')
    state = fields.Selection([('to_update', 'To Update'), ('updated', 'Updated'), ('locked', 'Locked')], string='status', default='to_update')

    @api.depends('bom_id')
    def _get_initial_bom_yield(self):
        for manuf_step in self:
            if manuf_step.bom_id:
                sfp_bom_line = manuf_step.bom_id.bom_line_ids.filtered(lambda line: line.product_id.categ_id.product_type == 'semi_finished_product')
                sfp_qty = sfp_bom_line[0].product_qty if sfp_bom_line else 1
                manuf_step.initial_bom_efficiency = manuf_step.bom_id.product_qty / sfp_qty * 100
            else:
                manuf_step.initial_bom_efficiency = 0

    @api.constrains('bom_efficiency')
    def _check_efficiency_domain(self):
        """
        Make sure that efficiency is in the range ]0; 100]
        """
        for manufacturing_step in self:
            if not 0 < manufacturing_step.bom_efficiency <= 100:
                raise UserError(_('The BOM yield must be greater than 0 and lower or equal than 100.'))

    @api.onchange('routing_id')
    def _onchange_routing_id(self):
        """
        Pre-filled the routing efficiency with the efficiency specified on the routing.
        """
        if self.routing_id:
            self.routing_efficiency_id = self.routing_id.routing_efficiency_id or self.routing_efficiency_id

    def update_product_manufacturing_step_action(self):
        """
        If self met the conditions than we either:
            - Create a new product.manufacturing.step record for configuring the next step in the manufacturing chain.
            - Stop the process because we have reach the last. The whole manufacturing chain is configured
        """
        self.ensure_one()
        # Before validating a manufacturing step we need to specified at least a BoM.
        if self.bom_id and (self.routing_id or self.bom_type != 'normal'):
            bom_semi_finished_products = self.bom_id.bom_line_ids.filtered(lambda line: line.product_id.categ_id.product_type == 'semi_finished_product')
            if len(bom_semi_finished_products) > 1:
                error_msg = _('{} BoM has more than one semi-finished product in its components list').format(self.bom_id.name_get())
                raise ValidationError(error_msg)
            # We create the next manufacturing step.
            elif bom_semi_finished_products:
                self.state = 'locked'
                vals = {
                    'product_id': bom_semi_finished_products.product_id.id,
                    'sequence': self.sequence + 1,
                    'sale_line_id': self.sale_line_id.id,
                }
                self.sale_line_id.update({'product_manufacture_step_ids': [(0, 0, vals)]})
            # We have reach the last step.
            else:
                self.state = 'updated'
                self.sale_line_id.configuration_is_done = True
        return self.sale_line_id.open_fp_configuration_view()

    def delete_product_manufacturing_step_action(self):
        """
        Delete a manufacturing step en then unlock the previous step.
        """
        self.ensure_one()
        sale_line = self.sale_line_id
        # after this, we lose references to self
        sale_line.update({'product_manufacture_step_ids': [(2, self.id, 0)]})
        # retrieve last manufacturing step and set its state to updatable (Unlock it)
        if sale_line._get_last_manufacturing_step():
            sale_line._get_last_manufacturing_step().state = 'to_update'
        # reset configuration done flag
        sale_line.configuration_is_done = False
        # reset calculated prices
        sale_line._reset_prices()
        # return view
        return sale_line.open_fp_configuration_view()
