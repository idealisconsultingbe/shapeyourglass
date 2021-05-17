# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AGCSaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Overridden Method
        We add in the context the pf_configure parameter in order to alter the behaviour of the standard.
        We block the confirmation of the SO if some finished productS are not totally configured.
        """
        fp_line = self.order_line.filtered(lambda line: line.product_id.categ_id.product_type == 'finished_product' and not line.no_config_needed)
        if fp_line:
            line_configuration_is_not_done = fp_line.filtered(lambda line: not line.configuration_is_done)
            if line_configuration_is_not_done:
                fp_missing_configuration = line_configuration_is_not_done.mapped('product_id')
                if len(fp_missing_configuration) > 1:
                    error_msg = _('Finished products {} are not configured.').format(', '.join(fp_missing_configuration.mapped(lambda product: '{}(ID:{})'.format(product.name, product.id))))
                else:
                    error_msg = _('Finished product {} is not configured.').format('{}(ID:{})'.format(fp_missing_configuration.name, fp_missing_configuration.id))
                raise ValidationError(error_msg)
            self = self.with_context(pf_configure=True)
        return super(AGCSaleOrder, self).action_confirm()

    def action_cancel(self):
        """
        Overridden Method
        If we cancel a Sale Order with finished product in its lines, then we also cancel every MO and PO created for the manufacturing of this product.
        """
        if self.state == 'sale':
            for fp_sale_line in self.order_line.filtered(lambda line: line.product_id.categ_id.product_type == 'finished_product'):
                for step_line in fp_sale_line.product_manufacture_step_ids:
                    if step_line.production_id and step_line.production_status in ('draft', 'confirmed'):
                        step_line.production_id.action_cancel()
                    if step_line.purchase_id and step_line.purchase_id.state in ('draft', 'sent', 'to_approve', 'purchase'):
                        step_line.purchase_id.button_cancel()
        return super(AGCSaleOrder, self).action_cancel()
