# -*- coding: utf-8 -*-
# Part of Idealis Consulting. See LICENSE file for full copyright and licensing details.

{
    'name': 'AGC Manufacturing',
    'summary': 'Module offering all expectations from AGC about Manufacturing',
    'version': '0.1',
    'description': """
Module offering all expectations from Expansion about Manufacturing
        """,
    'author': 'dwa@idealisconsulting.com - Idealis Consulting',
    'depends': [
        'base',
        'mrp',
        'stock',
    ],
    'data': [
        'views/agc_mrp_routing_views.xml',
        'views/agc_stock_traceability_report.xml',
    ],
    'installable': True,
    'auto_install': False,
}
