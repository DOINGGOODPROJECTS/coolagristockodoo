-- Rename the agriware_connector module to cool_agristock in-place at the database level.
--
-- Run this directly via psql against a database that currently has agriware_connector
-- installed, BEFORE deploying the renamed cool_agristock module code to that environment.
-- Odoo has no built-in "rename a module" operation and a module's own migration hooks only
-- fire for a module Odoo already recognizes by its current folder name, so this has to run
-- as a standalone script outside Odoo's update machinery. Once ir_module_module.name already
-- says 'cool_agristock' and the on-disk folder is also named cool_agristock, a normal Odoo
-- startup/update treats it as an ordinary already-installed module.
--
-- Usage:
--   pg_dump <database> > <database>_pre_rename_backup.dump   (always back up first)
--   psql <database> -f rename_agriware_to_cool_agristock.sql
--
-- Safe to run more than once: step 0 makes every later step a no-op if the module was
-- already renamed.

BEGIN;

-- Step 0: guard / idempotency check. Abort (rollback) if there's nothing to rename.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM ir_module_module WHERE name = 'agriware_connector'
    ) THEN
        RAISE EXCEPTION 'No agriware_connector module row found — already renamed, or module not installed. Nothing to do.';
    END IF;
END $$;

-- Step 1: rename the module's own 10 tables (metadata-only in Postgres — preserves all
-- data, indexes, and foreign keys; only auto-generated constraint/index names keep their
-- old prefix, which is cosmetic).
ALTER TABLE agriware_connection RENAME TO cool_agristock_connection;
ALTER TABLE agriware_api_key RENAME TO cool_agristock_api_key;
ALTER TABLE agriware_api_key_generate_wizard RENAME TO cool_agristock_api_key_generate_wizard;
ALTER TABLE agriware_external_system RENAME TO cool_agristock_external_system;
ALTER TABLE agriware_external_id_mapping RENAME TO cool_agristock_external_id_mapping;
ALTER TABLE agriware_uom_mapping RENAME TO cool_agristock_uom_mapping;
ALTER TABLE agriware_inventory_import RENAME TO cool_agristock_inventory_import;
ALTER TABLE agriware_inventory_import_line RENAME TO cool_agristock_inventory_import_line;
ALTER TABLE agriware_wms_transaction RENAME TO cool_agristock_wms_transaction;
ALTER TABLE agriware_dashboard RENAME TO cool_agristock_dashboard;

-- Step 2: rename the one field added to a core model.
ALTER TABLE res_partner RENAME COLUMN agriware_is_supplier TO cool_agristock_is_supplier;

-- Step 3: update ir_model rows for the module's own 10 models.
UPDATE ir_model
   SET model = replace(model, 'agriware.', 'cool_agristock.')
 WHERE model LIKE 'agriware.%';

-- Step 4: update ir_model_fields rows — both the owning model and, for relational fields,
-- the related model.
UPDATE ir_model_fields
   SET model = replace(model, 'agriware.', 'cool_agristock.'),
       relation = replace(relation, 'agriware.', 'cool_agristock.')
 WHERE model LIKE 'agriware.%' OR relation LIKE 'agriware.%';

-- Step 5: rename the res.partner field's own ir_model_fields row (name, not model/relation).
UPDATE ir_model_fields
   SET name = 'cool_agristock_is_supplier'
 WHERE model = 'res.partner' AND name = 'agriware_is_supplier';

-- Step 6: fix the one literal stored data value — the menu web_icon reference, which embeds
-- the module's technical name as a path prefix (not just an xmlid).
UPDATE ir_ui_menu
   SET web_icon = replace(web_icon, 'agriware_connector', 'cool_agristock')
 WHERE web_icon LIKE 'agriware_connector%';

-- Step 7: re-point every ir_model_data row owned by the old module to the new module name,
-- renaming the xmlid itself too. This single statement covers every xmlid category the
-- module owns (views, menus, actions, groups, rules, model/field auto-ids, constraints),
-- since they are all tracked through this one table.
UPDATE ir_model_data
   SET module = 'cool_agristock',
       name = replace(name, 'agriware', 'cool_agristock')
 WHERE module = 'agriware_connector';

-- Step 7b: a handful of xmlids (e.g. privilege_agriware_connector) embed the compound
-- token 'agriware_connector', not just 'agriware' — step 7's substitution leaves those as
-- '..._cool_agristock_connector', which doesn't match the renamed module's own id
-- (e.g. 'privilege_cool_agristock'). Collapse the stray '_connector' suffix so these line
-- up with the actual ids defined in the renamed XML, exactly as was done for the module's
-- source files during the code-side rename.
UPDATE ir_model_data
   SET name = replace(name, 'cool_agristock_connector', 'cool_agristock')
 WHERE module = 'cool_agristock' AND name LIKE '%cool_agristock_connector%';

-- Step 8: finally, rename the module itself in ir_module_module. Done last so steps 1-7
-- can still find their rows under the old module name while they run.
UPDATE ir_module_module
   SET name = 'cool_agristock'
 WHERE name = 'agriware_connector';

COMMIT;
