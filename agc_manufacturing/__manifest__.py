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
        'sale_margin',
        'product',
        'purchase',
        'stock',
        'stock_account',
        'mrp_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/agc_product_category_views.xml',
        'views/agc_mrp_routing_views.xml',
        'views/agc_mrp_routing_efficiency_views.xml',
        'views/agc_mrp_bom_views.xml',
        'views/agc_stock_production_lot_views.xml',
        'views/agc_stock_traceability_report.xml',
        'views/agc_sale_order_line_views.xml',
        'views/agc_sale_order_views.xml',
        'views/agc_mrp_production_views.xml'
    ],
    'installable': True,
    'auto_install': False,
}
