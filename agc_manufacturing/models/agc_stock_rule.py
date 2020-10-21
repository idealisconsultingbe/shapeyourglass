# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from itertools import groupby
from math import ceil

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError


class AGCStockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_purchase_order_line_step_vals(self, product_id, values):
        """
        Linked the purchase order line to its manufacturing step.
        """
        vals = {}
        if self.env.context.get('pf_configure', False):
            move_dest = values.get('move_dest_ids', False)
            so_line = move_dest._get_sale_order_line() if move_dest else False
            if so_line:
                step_line = so_line.find_next_unlinked_manufacturing_step(product_id)
                if step_line:
                    vals['product_manufacture_step_ids'] = [(4, step_line.id, 0)]
        return vals

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        """
        Overridden Method
        Linked the MO to its manufacturing step
        In the MO use the BoM and the routing specified in the manufacturing step.
        """

        def get_max_product_qty(so_line):
            """ Return max producible quantity in a bottom-up logic """
            mo_qty = dict()
            for step in so_line.product_manufacture_step_ids:
                if step.sequence == 1:
                    qty_needed = so_line.product_uom_qty
                    factor = ceil(qty_needed/so_line.finished_product_quantity)
                    factor = factor / step.bom_id.product_qty
                    factor = ceil(factor * (100 / step.bom_efficiency))
                    qty_to_produce = factor * step.bom_id.product_qty * so_line.finished_product_quantity
                else:
                    qty_needed = mo_qty[step.sequence-1]['raw_mat'][step.product_id.id]['qty_needed']
                    factor = qty_needed / step.bom_id.product_qty
                    factor = ceil(factor * (100 / step.bom_efficiency))
                    qty_to_produce = factor * step.bom_id.product_qty

                mo_qty.update({
                    step.sequence: {
                        'qty_needed': qty_needed,
                        'qty_to_produce': qty_to_produce,
                        'product_id': step.product_id.id,
                        'factor': factor,
                        'raw_mat': dict()}})

                for raw_line in step.bom_id.bom_line_ids:
                    mo_qty[step.sequence]['raw_mat'].update({raw_line.product_id.id: {
                        'qty_needed': raw_line.product_qty * factor,
                        'bom_qty': raw_line.product_qty}})

            i = max(mo_qty.keys()) - 1
            while i > 0:
                max_raw_mat_produced = mo_qty[i+1]['qty_to_produce']
                raw_mat_product_id = mo_qty[i+1]['product_id']
                raw_mat_bom_qty = mo_qty[i]['raw_mat'][raw_mat_product_id]['bom_qty']
                factor = ceil(max_raw_mat_produced / raw_mat_bom_qty)
                mo_qty[i]['qty_to_produce'] = (mo_qty[i]['qty_to_produce'] / mo_qty[i]['factor']) * factor
                mo_qty[i]['max_factor'] = factor
                i -= 1
            return mo_qty[1]['qty_to_produce']

        res = super(AGCStockRule, self)._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        if self.env.context.get('pf_configure', False):
            move_dest = values.get('move_dest_ids', False)
            so_line = move_dest._get_sale_order_line() if move_dest else False
            if so_line:
                step_line = so_line.find_next_unlinked_manufacturing_step(product_id)
                if step_line.sequence == 1:
                    res['product_qty'] = get_max_product_qty(so_line)
                res.update({
                    'bom_id': step_line.bom_id.id,
                    'routing_id': step_line.routing_id.id,
                    'product_manufacture_step_ids': [(4, step_line.id, 0)]
                })

        return res

    @api.model
    def _run_buy(self, procurements):
        """
        Overwrite standard method.
        At the end of the run_buy process automatically confirm the PO if we are in the pf_configure process and if it has at least one line linked
        to a product manufacturing step.
        """
        procurements_by_po_domain = defaultdict(list)
        for procurement, rule in procurements:

            # Get the schedule date in order to find a valid seller
            procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])
            schedule_date = (procurement_date_planned - relativedelta(days=procurement.company_id.po_lead))

            supplier = procurement.product_id._select_seller(
                partner_id=procurement.values.get("supplier_id"),
                quantity=procurement.product_qty,
                date=schedule_date.date(),
                uom_id=procurement.product_uom)

            if not supplier:
                msg = _(
                    'There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.') % (
                          procurement.product_id.display_name)
                raise UserError(msg)

            partner = supplier.name
            # we put `supplier_info` in values for extensibility purposes
            procurement.values['supplier'] = supplier
            procurement.values['propagate_date'] = rule.propagate_date
            procurement.values['propagate_date_minimum_delta'] = rule.propagate_date_minimum_delta
            procurement.values['propagate_cancel'] = rule.propagate_cancel

            domain = rule._make_po_get_domain(procurement.company_id, procurement.values, partner)
            procurements_by_po_domain[domain].append((procurement, rule))

        for domain, procurements_rules in procurements_by_po_domain.items():
            # Get the procurements for the current domain.
            # Get the rules for the current domain. Their only use is to create
            # the PO if it does not exist.
            procurements, rules = zip(*procurements_rules)

            # Get the set of procurement origin for the current domain.
            origins = set([p.origin for p in procurements])
            # Check if a PO exists for the current domain.
            po = self.env['purchase.order'].sudo().search([dom for dom in domain], limit=1)
            company_id = procurements[0].company_id
            if not po:
                # We need a rule to generate the PO. However the rule generated
                # the same domain for PO and the _prepare_purchase_order method
                # should only uses the common rules's fields.
                vals = rules[0]._prepare_purchase_order(company_id, origins, [p.values for p in procurements])
                # The company_id is the same for all procurements since
                # _make_po_get_domain add the company in the domain.
                po = self.env['purchase.order'].with_context(force_company=company_id.id).sudo().create(vals)
            else:
                # If a purchase order is found, adapt its `origin` field.
                if po.origin:
                    missing_origins = origins - set(po.origin.split(', '))
                    if missing_origins:
                        po.write({'origin': po.origin + ', ' + ', '.join(missing_origins)})
                else:
                    po.write({'origin': ', '.join(origins)})

            procurements_to_merge = self._get_procurements_to_merge(procurements)
            procurements = self._merge_procurements(procurements_to_merge)

            po_lines_by_product = {}
            grouped_po_lines = groupby(
                po.order_line.filtered(lambda l: not l.display_type and l.product_uom == l.product_id.uom_po_id).sorted(
                    'product_id'), key=lambda l: l.product_id.id)
            for product, po_lines in grouped_po_lines:
                po_lines_by_product[product] = self.env['purchase.order.line'].concat(*list(po_lines))
            po_line_values = []
            for procurement in procurements:
                po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
                po_line = po_lines._find_candidate(*procurement)

                if po_line:
                    # If the procurement can be merge in an existing line. Directly
                    # write the new values on it.
                    vals = self._update_purchase_order_line(procurement.product_id,
                                                            procurement.product_qty, procurement.product_uom,
                                                            company_id,
                                                            procurement.values, po_line)
                    po_line.write(vals)
                else:
                    # If it does not exist a PO line for current procurement.
                    # Generate the create values for it and add it to a list in
                    # order to create it in batch.
                    partner = procurement.values['supplier'].name
                    po_line_values.append(self._prepare_purchase_order_line(
                        procurement.product_id, procurement.product_qty,
                        procurement.product_uom, procurement.company_id,
                        procurement.values, po))
            self.env['purchase.order.line'].sudo().create(po_line_values)
        # Custom changes happen here
        if self.env.context.get('pf_configure', False):
            if po.order_line.filtered(lambda line: line.product_manufacture_step_ids):
                po.button_confirm()
        # end

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        """
        Overridden Method
        Link the PO line to its manufacturing step and use the BoM and routing specified in it.
        """
        res = super(AGCStockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)
        res.update(self._get_purchase_order_line_step_vals(product_id, values))
        return res
