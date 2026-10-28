# Cool Agristock navigation

The connector opens on **Overview**, followed by five operational areas. It uses
Odoo Inventory's existing records, permissions, searches and workflows.

| Area | Available screens |
| --- | --- |
| Products & Inventory | Products, Inventory Overview, Stock Adjustments, Agricultural Lots & Serial Numbers, Inventory Imports |
| Warehouses & Locations | Warehouses, Storage Locations |
| Warehouse Operations | Goods Received, Dispatches & Deliveries, Stock Movements |
| Suppliers | Supplier Records, Supplier Synchronization mappings |
| Integrations & Configuration | Connected WMS Systems, Receipt & Dispatch History, Cancelled WMS Operations, Configuration |

Configuration contains API Management (keys and key generation), external ID
mappings, unit mappings, and User Permissions. The last item requires Odoo Settings
access. Automatic adjustment settings live on each Connected WMS System, where
they apply. There is no scheduler or outbound connection setting: synchronization
is initiated by the WMS through the API.

## Overview and audit information

Overview reads real records for the companies selected in Odoo: active registered
WMS systems, valid key metadata, receipt/dispatch counts, completed/cancelled
operations, the latest transaction, catalog mappings, and inventory counts needing
review or rejected. Connector administrators also see the five most recently
received transactions whose warehouse operations are complete. Quick access opens
products, warehouses, receipts, dispatches, inventory, suppliers, lots and imports.

Registered systems and valid keys show configuration, **not live connectivity**.
The connector does not track WMS heartbeats. Request failures are returned to the
WMS client and are not persisted as an API error log; no fictitious Failed
Synchronizations menu or success/failure statistics are presented. Cancelled
operations and rejected inventory counts are explicitly labeled as such.

Receipt & Dispatch History shows the external WMS and reference, arrival time,
current native picking status, completion date, and the linked picking. Search by
reference, system or transfer; filter completed, cancelled or in-progress records,
and group by WMS or category. Inventory Imports has status/date filters and WMS,
warehouse and status grouping, alongside existing review and audit fields.

External ID mappings identify which WMS owns each catalog identity (products,
warehouses, locations, lots and suppliers). Filter or group them by WMS and record
type, then use **Open Odoo Record**. Mapping creation time is explicitly labeled;
it is not a last-sync timestamp, which catalog endpoints do not currently track.
Supplier Synchronization opens the same mappings filtered to suppliers.

## Permissions

- Inventory users can open Overview and operational screens. Native Odoo access
  rules still determine which records they can read or modify.
- Connector administrators manage WMS registrations, API credentials, mappings
  and transaction history. They need no Odoo Settings access for these functions.
- Only inventory managers can approve or reject staged inventory imports.
- Only users with Odoo Settings access see User Permissions.
- The unfinished legacy outbound WMS connection screen remains hidden behind
  Technical Features and is not advertised as a working integration.

## Automatic stock adjustments

Each WMS must explicitly opt in and have a positive maximum variance. Automatic
application uses native Odoo inventory adjustments and leaves completed stock
moves. It rejects stock split across packages/owners, ambiguous duplicate quants,
and pending manual counts instead of overwriting a warehouse user's work. The
staged review API remains available and does not change stock automatically.

## Upgrade and verification

Upgrade `cool_agristock` with Odoo 19. The module is listed as an application.
The menu layout preserves XML identifiers for existing installations and does not
modify the native Inventory menus. The unused intermediate WMS category is
inactive; its functional screen is moved directly under Integrations & Configuration.

Run the connector test suite only on a disposable database. Menu regressions
exercise dashboard access, quick links, native server actions, model permissions
and view loading as ordinary inventory users and connector administrators. API
regressions cover location and supplier synchronization, stock adjustments,
authentication, company isolation and the other existing endpoints.
