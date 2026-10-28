{
    "name": "Cool Agristock",
    "version": "19.0.3.0.0",
    "summary": "Connect Odoo with Cool Agristock Warehouse Management",
    "description": """
Cool Agristock — Open-Source Warehouse Management for Agribusinesses.

This module integrates an existing Cool Agristock installation
with Odoo ERP.

Cool Agristock remains a standalone application.
The connector enables communication and data synchronization
between Cool Agristock and Odoo.
    """,
    "category": "Inventory/Inventory",
    "author": "Cool Agristock",
    "website": "https://github.com/DOINGGOODPROJECTS/coolagristockodoo",
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
        "security/cool_agristock_security.xml",
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
