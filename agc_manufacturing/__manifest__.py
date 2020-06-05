# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.
{
    'name': 'AGC Manufacturing',
    'summary': 'Module offering all expectations from AGC about Manufacturing',
    'version': '13.0.0.1',
    'description': """
            Module offering all expectations from AGC about Manufacturing
        """,
    'author': 'pfi@idealisconsulting.com, dwa@idealisconsulting.com - Idealis Consulting',
    'depends': [
        'base',
        'mrp',
        'sale',
        'product',
        'purchase',
        'stock',
        'stock_account',
        'mrp_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/agc_product_category_view.xml',
        'views/agc_mrp_routing_view.xml',
        'views/agc_mrp_routing_efficiency_view.xml',
        'views/agc_mrp_bom_view.xml',
        'views/agc_stock_production_lot_view.xml',
        'views/agc_stock_traceability_report.xml',
        'views/agc_sale_order_line_view.xml',
        'views/agc_sale_order_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
