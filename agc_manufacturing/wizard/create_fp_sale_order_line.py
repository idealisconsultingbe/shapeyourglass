# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
from math import ceil

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import get_lang


class CreateFPSaleOrderLine(models.TransientModel):
    _name = 'create.fp.sale.order.line'
    _description = 'Create Confirmed Sale Order Line with Finished Product'

    def _default_allowed_category_ids(self):
        return [(6, 0, self.env['product.category'].search([('product_type', '=', 'finished_product')]).ids)]

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    order_id = fields.Many2one('sale.order', string='Order Reference', required=True)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    product_id = fields.Many2one('product.product', string='Product', change_default=True, required=True, check_company=True)  # Unrequired company
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    product_manufacture_step_ids = fields.Many2many('product.manufacturing.step', 'wiz_manufacturing_step_rel', 'wiz_id', 'manuf_step_id', string='Finished Product Manufacturing Step')
    # finished_product_quantity = fields.Integer(string='Finished Products / Mothersheet', default=1, required=1, help='Must be expressed in the unit of measure of the BoM selected for producing the Finished Product (the UoM of the BoM selected at the first line.)')
    # max_producible_quantity = fields.Integer(string='Max Producible Qty', compute='_compute_max_producible_qty', help='The quantity which is going to be produced if we have an efficiency of 100% for each step.')
    configuration_is_done = fields.Boolean(string='Finished Product Configuration is Done', default=False, help='Technical field that helps to know if the Finished Product configuration is done.')

    allowed_category_ids = fields.Many2many('product.category', 'wiz_product_category_rel', 'wiz_id', 'category_id', default=_default_allowed_category_ids, string='Allowed Product Categories', help='Technical field used to filter finished products')
    updated_manufacturing_step = fields.Boolean(string='Update Manufacturing Step')
    deleted_manufacturing_step = fields.Boolean(string='Delete Manufacturing Step')

    # @api.depends('product_manufacture_step_ids.bom_id.product_qty', 'product_manufacture_step_ids.bom_efficiency',
    #              'product_manufacture_step_ids.bom_id.bom_line_ids', 'product_manufacture_step_ids.product_id',
    #              'product_manufacture_step_ids.sequence', 'finished_product_quantity', 'product_uom_qty', 'configuration_is_done')
    # def _compute_max_producible_qty(self):
    #     """ Compute the maximum producible quantity"""
    #     for wiz in self:
    #         wiz.max_producible_quantity = 0
    #         if wiz.configuration_is_done:
    #             max_product_qty = wiz.get_max_product_qty()
    #             if max_product_qty:
    #                 wiz.max_producible_quantity = max_product_qty[1]['qty_to_produce']

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        Logic coming from standard product_id_change() method of sale order lines.
        Product attributes are no longuer considered to compute product name since we do not handle those attributes in the wizard
        """
        if not self.product_id:
            self.product_manufacture_step_ids.unlink()
            return

        vals = {}

        # create first manufacturing step
        product_manufacture_step = self.env['product.manufacturing.step'].create({'product_id': self.product_id.id, 'sequence': 1})
        vals['product_manufacture_step_ids'] = [(6, 0, [product_manufacture_step.id])]

        if not self.product_uom_id or (self.product_id.uom_id.id != self.product_uom_id.id):
            vals['product_uom_id'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom_id.id
        )
        # do not retrieve decription of variants
        vals.update(name=product.get_product_multiline_description_sale())

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_ids, self.company_id)
        self.update(vals)

        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result

    @api.onchange('product_uom_id', 'product_uom_qty')
    def _onchange_product_uom(self):
        """ Exactly the same method than the standard method product_uom_change() on sale order lines """
        if not self.product_uom_id or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom_id.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_ids, self.company_id)

    @api.onchange('product_id', 'price_unit', 'product_uom_id', 'product_uom_qty', 'tax_ids')
    def _onchange_discount(self):
        """ Exactly the same method than the standard method _onchange_discount() on sale order lines """
        if not (self.product_id and self.product_uom_id and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom_id.id)

        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom_id, self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount

    @api.onchange('updated_manufacturing_step')
    def _onchange_updated_manufacturing_step(self):
        """
        If conditions are met:
            - Create a new product.manufacturing.step record for configuring the next step in the manufacturing chain.
            - Stop the process when reaching the final step: the whole manufacturing chain is configured

        In order to update manufacturing steps it is not possible to apply logic from sale order lines.
        Firstly, it is not possible to keep buttons on each lines. Those buttons call methods that need a reference to parent object.
        We lost this relationship by using a wizard and cutting reference to sale order line.
        Secondly, wizard window is closed when clicking on a button. This force us to create a new wizard and passing all information by context
        to this new wizard. It could have worked but this will trigger _onchange_product_id() method and will erase all manufacturing steps.
        In order to tackle those inconveniences, we could simulate a button with a boolean: use CSS on field label to create a button
        and write an onchange method that applies logic if boolean changes.
        """
        # abort if there is no product
        if not self.product_id:
            return
        # retrieve last manufacturing step
        sorted_manufacturing_steps = self.product_manufacture_step_ids.sorted(key=lambda x: x.sequence, reverse=True)
        last_manufacturing_step = sorted_manufacturing_steps[0] if len(sorted_manufacturing_steps) > 1 else sorted_manufacturing_steps

        vals = {}
        # if there is no manufacturing steps
        if not last_manufacturing_step:
            vals.update({'sequence': 1, 'product_id': self.product_id.id})
        # if there is at least one manufacturing step correctly set up
        elif last_manufacturing_step and last_manufacturing_step.bom_id and last_manufacturing_step.bom_efficiency \
                and ((last_manufacturing_step.routing_id and last_manufacturing_step.routing_efficiency_id)
                     or last_manufacturing_step.bom_type != 'normal'):
            bom_semi_finished_products = last_manufacturing_step.bom_id.bom_line_ids.filtered(lambda line: line.product_id.categ_id.product_type == 'semi_finished_product')
            if len(bom_semi_finished_products) > 1:
                error_msg = _('{} BoM has more than one semi-finished product in its components list').format(last_manufacturing_step.bom_id.name_get())
                raise ValidationError(error_msg)
            # creating a new step
            elif bom_semi_finished_products:
                last_manufacturing_step.state = 'locked'
                vals.update({
                    'product_id': bom_semi_finished_products.product_id.id,
                    'sequence': last_manufacturing_step.sequence + 1,
                })
            # We have reached the final step
            else:
                last_manufacturing_step.state = 'updated'
                self.configuration_is_done = True
                return
        else:
            return
        self.update({'product_manufacture_step_ids': [(0, 0, vals)]})

    @api.onchange('deleted_manufacturing_step')
    def _onchange_deleted_manufacturing_step(self):
        """
        Simulate remove button that deletes a manufacturing step and unlock the previous step
        see: _onchange_updated_manufacturing_step()
        """
        # abort if there is no product
        if not self.product_id:
            return

        # retrieve last manufacturing step
        sorted_manufacturing_steps = self.product_manufacture_step_ids.sorted(key=lambda x: x.sequence, reverse=True)
        last_manufacturing_step = sorted_manufacturing_steps[0] if len(sorted_manufacturing_steps) > 1 else sorted_manufacturing_steps
        penultimate_manufacturing_step = sorted_manufacturing_steps[1] if len(sorted_manufacturing_steps) >= 2 else False

        if last_manufacturing_step:
            self.update({'product_manufacture_step_ids': [(2, last_manufacturing_step.id, 0)]})
            # set penultimate manufacturing step state to updatable (Unlock it)
            if penultimate_manufacturing_step:
                penultimate_manufacturing_step.state = 'to_update'
            # reset configuration done flag
            self.configuration_is_done = False

    def button_add_line(self):
        self.ensure_one()
        if self.configuration_is_done:
            vals = {
                'order_id': self.order_id.id,
                'name': self.name,
                'sequence': self.sequence,
                'price_unit': self.price_unit,
                'tax_id': [(6, 0, self.tax_ids.ids)],
                'discount': self.discount,
                'product_id': self.product_id.id,
                'product_uom_qty': self.product_uom_qty,
                'product_uom': self.product_uom_id.id,
                'configuration_is_done': self.configuration_is_done,
                # 'finished_product_quantity': self.finished_product_quantity,
                'product_manufacture_step_ids': [(0, 0, self.product_manufacture_step_ids.ids)]
            }
            line = self.env['sale.order.line'].create(vals)
            # self.product_manufacture_step_ids.write({'sale_line_id': line.id})

    # def get_max_product_qty(self):
    #     """Compute the min qty needed and the maximum producible quantity for each MO"""
    #     self.ensure_one()
    #     mo_qty = dict()
    #     for step in self.product_manufacture_step_ids:
    #         if step.sequence == 1:
    #             qty_needed = self.product_uom_qty
    #             factor = ceil(qty_needed / self.finished_product_quantity)
    #             factor = factor / (step.bom_id.product_qty or 1.0)
    #             factor = ceil(factor * (100 / step.bom_efficiency))
    #             qty_to_produce = factor * step.bom_id.product_qty * self.finished_product_quantity
    #         else:
    #             qty_needed = mo_qty[step.sequence - 1]['raw_mat'][step.product_id.id]['qty_needed']
    #             factor = qty_needed / (step.bom_id.product_qty or 1.0)
    #             factor = ceil(factor * (100 / step.bom_efficiency))
    #             qty_to_produce = factor * step.bom_id.product_qty
    #
    #         mo_qty.update({
    #             step.sequence: {
    #                 'qty_needed': qty_needed,
    #                 'qty_to_produce': qty_to_produce,
    #                 'product_id': step.product_id.id,
    #                 'factor': factor,
    #                 'raw_mat': dict()}})
    #
    #         for raw_line in step.bom_id.bom_line_ids:
    #             mo_qty[step.sequence]['raw_mat'].update({raw_line.product_id.id: {
    #                 'qty_needed': raw_line.product_qty * factor,
    #                 'bom_qty': raw_line.product_qty}})
    #     if mo_qty:
    #         i = max(mo_qty.keys()) - 1
    #         while i > 0:
    #             max_raw_mat_produced = mo_qty[i + 1]['qty_to_produce']
    #             raw_mat_product_id = mo_qty[i + 1]['product_id']
    #             raw_mat_bom_qty = mo_qty[i]['raw_mat'][raw_mat_product_id]['bom_qty']
    #             factor = ceil(max_raw_mat_produced / raw_mat_bom_qty)
    #             mo_qty[i]['qty_to_produce'] = (mo_qty[i]['qty_to_produce'] / mo_qty[i]['factor']) * factor
    #             mo_qty[i]['max_factor'] = factor
    #             i -= 1
    #     return mo_qty

    def _get_display_price(self, product):
        """
        Logic coming from standard _get_display_price() method of sale order lines.
        Product attributes are no longuer considered to compute the display price since we do not handle those attributes in the wizard
        """
        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.order_id.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom_id, self.order_id.pricelist_id.id)
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """ Exactly the same method than the method _get_real_price_currency() on sale order lines """
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id

    def _compute_tax_id(self):
        """ Exactly the same method than the method _compute_tax_id() on sale order lines """
        for wiz in self:
            fpos = wiz.order_id.fiscal_position_id or wiz.order_id.partner_id.property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = wiz.product_id.taxes_id.filtered(lambda r: not wiz.company_id or r.company_id == wiz.company_id)
            wiz.tax_ids = fpos.map_tax(taxes, wiz.product_id, wiz.order_id.partner_shipping_id) if fpos else taxes
