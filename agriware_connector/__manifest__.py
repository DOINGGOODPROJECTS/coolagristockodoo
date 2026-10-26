{
    "name": "AgriWare Connector",
    "version": "19.0.2.0.1",
    "summary": "Connect Odoo with AgriWare Warehouse Management",
    "description": """
AgriWare — Open-Source Warehouse Management for Agribusinesses.

This module integrates an existing AgriWare installation
with Odoo ERP.

AgriWare remains a standalone application.
The connector enables communication and data synchronization
between AgriWare and Odoo.
    """,
    "category": "Inventory/Inventory",
    "author": "Cool Agristock",
    "website": "https://github.com/DOINGGOODPROJECTS/agriwareodoo",
    "license": "LGPL-3",
    "images": [
        "static/description/apps_listing_screenshot.png",
    ],
    "depends": [
        "base",
        "connector",
        "stock",
    ],

    "data": [
        "security/agriware_security.xml",
        "security/ir.model.access.csv",
        "views/connection_views.xml",
        "views/api_key_views.xml",
        "views/external_system_views.xml",
        "views/uom_mapping_views.xml",
        "views/inventory_import_views.xml",
        "views/dashboard_views.xml",
        "views/navigation_views.xml",
        "views/suppliers_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
