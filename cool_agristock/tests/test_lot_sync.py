import json

from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockLotSync(CoolAgristockApiCommon):
    """POST/PATCH/GET /cool_agristock/api/v1/lots, lot-level inventory import
    reconciliation, and receipt/dispatch lot integration (Phase F)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        internal_group = cls.env.ref("base.group_user")
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")

        # See test_inventory_import.py's setUpClass for why this is
        # necessary -- the shared fixtures default to "Units", but this
        # suite's payloads use "kg" throughout.
        kg = cls.env.ref("uom.product_uom_kgm")
        cls.product.uom_id = kg
        cls.lot_tracked_product.uom_id = kg
        cls.serial_tracked_product.uom_id = kg

        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Primary WMS", "code": "primary_wms_f", "company_id": cls.env.company.id,
        })

        ApiKey = cls.env["cool_agristock.api.key"].with_user(cls.admin_user)
        cls.bound_raw_key, cls.bound_key_record = ApiKey.generate_key(
            name="Bound WMS Key F", company=cls.env.company, external_system=cls.external_system,
        )

        Mapping = cls.env["cool_agristock.external.id.mapping"].sudo()
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "stock.warehouse", "external_id": "WH-001", "res_id": cls.warehouse.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "product.product", "external_id": "AGRI-001", "res_id": cls.product.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "product.product", "external_id": "AGRI-LOT", "res_id": cls.lot_tracked_product.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "product.product", "external_id": "AGRI-SERIAL", "res_id": cls.serial_tracked_product.id,
        })

        cls.unbound_only_company = cls.env["res.company"].create({
            "name": "Phase F Unbound-Only Company",
        })
        cls.unbound_only_admin_user = cls.env["res.users"].create({
            "name": "Phase F Unbound-Only Admin", "login": "cool_agristock_phasef_unbound_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.unbound_only_company.id])],
            "company_id": cls.unbound_only_company.id,
        })
        cls.unbound_raw_key, cls.unbound_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.unbound_only_admin_user
        ).generate_key(name="Unbound Key F", company=cls.unbound_only_company)

        cls.other_company = cls.env["res.company"].create({"name": "Phase F Other Company"})
        cls.other_admin_user = cls.env["res.users"].create({
            "name": "Phase F Other Company Admin", "login": "cool_agristock_phasef_other_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.other_company.id])], "company_id": cls.other_company.id,
        })
        cls.other_external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Other Co WMS", "code": "primary_wms_f", "company_id": cls.other_company.id,
        })
        cls.other_raw_key, cls.other_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.other_admin_user
        ).generate_key(
            name="Other Co Key F", company=cls.other_company, external_system=cls.other_external_system,
        )

        cls.second_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Second WMS Same Co", "code": "second_wms_f", "company_id": cls.env.company.id,
        })
        cls.second_system_raw_key, cls.second_system_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.admin_user
        ).generate_key(
            name="Second System Key F", company=cls.env.company, external_system=cls.second_system,
        )

    # -- helpers ----------------------------------------------------------

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _body(self, response):
        return json.loads(response.content)

    def _post_lot(self, key, data):
        return self.url_open("/cool_agristock/api/v1/lots", json=data, headers=self._headers(key))

    def _patch_lot(self, key, external_id, data):
        return self.url_open(
            f"/cool_agristock/api/v1/lots/{external_id}", json=data,
            headers=self._headers(key), method="PATCH",
        )

    def _post_import(self, key, data):
        return self.url_open(
            "/cool_agristock/api/v1/inventory-adjustments", json=data, headers=self._headers(key),
        )

    def _lot_payload(self, external_id="LOT-001", product_external_id="AGRI-LOT", name="COCOA-2026-001"):
        return {"external_id": external_id, "product_external_id": product_external_id, "name": name}

    def _create_receipt(self, product, quantity):
        return self._as_api_user("/cool_agristock/api/v1/receipts", method="POST", json={
            "external_reference": "COOL_AGRISTOCK-RCPT-LOT-%s" % product.id,
            "warehouse_id": self.warehouse.id,
            "supplier_id": self.partner.id,
            "products": [{"product_id": product.id, "quantity": quantity}],
        })

    def _validate_receipt(self, key, receipt_id, data):
        return self.url_open(
            f"/cool_agristock/api/v1/receipts/{receipt_id}/validate",
            json=data, headers=self._headers(key), method="POST",
        )

    def _create_dispatch(self, product, quantity, reference):
        return self._as_api_user("/cool_agristock/api/v1/dispatches", method="POST", json={
            "external_reference": reference,
            "warehouse_id": self.warehouse.id,
            "customer_id": self.partner.id,
            "products": [{"product_id": product.id, "quantity": quantity}],
        })

    def _validate_dispatch(self, key, dispatch_id, data):
        return self.url_open(
            f"/cool_agristock/api/v1/dispatches/{dispatch_id}/validate",
            json=data, headers=self._headers(key), method="POST",
        )

    # -- 1. Lot creation ----------------------------------------------------

    def test_create_lot(self):
        response = self._post_lot(self.bound_raw_key, self._lot_payload())
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        lot = self.env["stock.lot"].browse(body["lot_id"])
        self.assertEqual(lot.name, "COCOA-2026-001")
        self.assertEqual(lot.product_id, self.lot_tracked_product)
        self.assertEqual(lot.company_id, self.env.company)

    def test_create_lot_untracked_product_rejected(self):
        response = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-UNTRACKED", product_external_id="AGRI-001",
        ))
        self.assertEqual(response.status_code, 422)

    def test_create_lot_unknown_product_rejected(self):
        response = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-UNKNOWN", product_external_id="AGRI-DOES-NOT-EXIST",
        ))
        self.assertEqual(response.status_code, 404)

    def test_create_lot_missing_name_rejected(self):
        payload = self._lot_payload(external_id="LOT-NO-NAME")
        payload["name"] = ""
        response = self._post_lot(self.bound_raw_key, payload)
        self.assertEqual(response.status_code, 400)

    def test_create_lot_unsupported_field_rejected(self):
        payload = self._lot_payload(external_id="LOT-BAD-FIELD")
        payload["expiration_date"] = "2026-12-31"
        response = self._post_lot(self.bound_raw_key, payload)
        self.assertEqual(response.status_code, 400)

    def test_create_serial(self):
        response = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="SERIAL-001", product_external_id="AGRI-SERIAL", name="SERIAL-0001",
        ))
        self.assertEqual(response.status_code, 201)

    # -- 2. Lot updates ------------------------------------------------------

    def test_update_lot_name(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-UPDATE"))
        response = self._patch_lot(self.bound_raw_key, "LOT-UPDATE", {"name": "COCOA-2026-001-R2"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._body(response)["name"], "COCOA-2026-001-R2")

    def test_update_lot_name_blocked_after_stock_history(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-HISTORY"))

        create_resp = self._create_receipt(self.lot_tracked_product, 20)
        receipt_id = create_resp.json()["receipt_id"]
        validate_resp = self._validate_receipt(self.bound_raw_key, receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-LOT-%s" % self.lot_tracked_product.id,
            "received_quantities": [{
                "product_id": self.lot_tracked_product.id, "quantity": 20,
                "lot_external_id": "LOT-HISTORY",
            }],
        })
        self.assertEqual(validate_resp.status_code, 200)

        response = self._patch_lot(self.bound_raw_key, "LOT-HISTORY", {"name": "RENAMED"})
        self.assertEqual(response.status_code, 409)

    def test_update_unknown_lot_returns_404(self):
        response = self._patch_lot(self.bound_raw_key, "LOT-NEVER-CREATED", {"name": "Nope"})
        self.assertEqual(response.status_code, 404)

    # -- 3. Idempotency / duplicate -------------------------------------------

    def test_duplicate_lot_external_id_rejected(self):
        first = self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-DUP"))
        self.assertEqual(first.status_code, 201)
        second = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-DUP", name="Different Name",
        ))
        self.assertEqual(second.status_code, 409)

    def test_conflicting_product_assignment_for_existing_name_rejected(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-A", name="SHARED-NAME",
        ))
        response = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-B", name="SHARED-NAME",
        ))
        self.assertEqual(response.status_code, 409)

    # -- Security / isolation --------------------------------------------------

    def test_unbound_key_rejected_for_lot_creation(self):
        response = self._post_lot(self.unbound_raw_key, self._lot_payload(external_id="LOT-UNBOUND"))
        self.assertEqual(response.status_code, 403)

    def test_unbound_key_still_works_for_get(self):
        response = self.url_open("/cool_agristock/api/v1/lots", headers=self._headers(self.unbound_raw_key))
        self.assertEqual(response.status_code, 200)

    def test_cross_company_lot_creation_isolated(self):
        other_product = self.env["product.product"].sudo().create({
            "name": "Other Co Tracked Product", "type": "consu",
            "is_storable": True, "tracking": "lot", "company_id": False,
        })
        self.env["cool_agristock.external.id.mapping"].sudo().create({
            "company_id": self.other_company.id, "external_system_id": self.other_external_system.id,
            "res_model": "product.product", "external_id": "AGRI-LOT", "res_id": other_product.id,
        })
        response_a = self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-CROSS"))
        response_b = self._post_lot(self.other_raw_key, self._lot_payload(external_id="LOT-CROSS"))
        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 201)
        self.assertNotEqual(
            self._body(response_a)["lot_id"], self._body(response_b)["lot_id"],
        )

    def test_cross_system_lot_not_found(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-CROSS-SYS"))
        patch_response = self._patch_lot(self.second_system_raw_key, "LOT-CROSS-SYS", {"name": "Hijacked"})
        self.assertEqual(patch_response.status_code, 404)

    def test_inactive_external_system_rejected(self):
        self.external_system.sudo().active = False
        try:
            response = self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-INACTIVE"))
            self.assertEqual(response.status_code, 403)
        finally:
            self.external_system.sudo().active = True

    # -- Lot-level inventory import -------------------------------------------

    def test_lot_level_inventory_import(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-IMPORT"))
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-LOT-STOCK-001",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-LOT", "lot_external_id": "LOT-IMPORT",
                "quantity": 2500, "unit": "kg",
            }],
        })
        self.assertEqual(response.status_code, 201)
        line = self._body(response)["lines"][0]
        self.assertEqual(line["current_odoo_quantity"], 0.0)
        self.assertEqual(line["proposed_difference"], 2500.0)

    def test_lot_level_reconciliation_does_not_aggregate_lots(self):
        lot_a_resp = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-RECON-A", name="LOT-A",
        ))
        lot_b_resp = self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-RECON-B", name="LOT-B",
        ))
        lot_a = self.env["stock.lot"].browse(self._body(lot_a_resp)["lot_id"])
        lot_b = self.env["stock.lot"].browse(self._body(lot_b_resp)["lot_id"])

        self.env["stock.quant"]._update_available_quantity(
            self.lot_tracked_product, self.warehouse.lot_stock_id, 1000, lot_id=lot_a,
        )
        self.env["stock.quant"]._update_available_quantity(
            self.lot_tracked_product, self.warehouse.lot_stock_id, 7000, lot_id=lot_b,
        )

        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-LOT-STOCK-002",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-LOT", "lot_external_id": "LOT-RECON-A",
                "quantity": 1000, "unit": "kg",
            }],
        })
        self.assertEqual(response.status_code, 201)
        line = self._body(response)["lines"][0]
        # Only lot A's 1000 kg is considered -- lot B's 7000 kg is
        # never aggregated in, even though it's the same product/location.
        self.assertEqual(line["current_odoo_quantity"], 1000.0)
        self.assertEqual(line["proposed_difference"], 0.0)

    def test_tracked_product_without_lot_still_rejected(self):
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-NO-LOT",
            "warehouse_external_id": "WH-001",
            "lines": [{"product_external_id": "AGRI-LOT", "quantity": 500, "unit": "kg"}],
        })
        self.assertEqual(response.status_code, 422)

    def test_untracked_product_with_lot_external_id_rejected(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-MISPLACED"))
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-MISPLACED-LOT",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-001", "lot_external_id": "LOT-MISPLACED",
                "quantity": 100, "unit": "kg",
            }],
        })
        self.assertEqual(response.status_code, 422)

    def test_unknown_lot_external_id_rejected(self):
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-UNKNOWN-LOT",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-LOT", "lot_external_id": "LOT-GHOST",
                "quantity": 100, "unit": "kg",
            }],
        })
        self.assertEqual(response.status_code, 404)

    def test_lot_belonging_to_wrong_product_rejected(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="LOT-WRONG-PRODUCT", product_external_id="AGRI-LOT",
        ))
        # AGRI-SERIAL is a *different* tracked product -- this lot was
        # created against AGRI-LOT, not it.
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-WRONG-LOT-PRODUCT",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-SERIAL", "lot_external_id": "LOT-WRONG-PRODUCT",
                "quantity": 1, "unit": "unit",
            }],
        })
        self.assertEqual(response.status_code, 422)

    def test_serial_quantity_must_be_exactly_one(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(
            external_id="SERIAL-QTY", product_external_id="AGRI-SERIAL", name="SERIAL-QTY-0001",
        ))
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-SERIAL-QTY",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-SERIAL", "lot_external_id": "SERIAL-QTY",
                "quantity": 5, "unit": "unit",
            }],
        })
        self.assertEqual(response.status_code, 422)

    def test_stale_detection_applies_to_lot_lines(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-STALE"))
        response = self._post_import(self.bound_raw_key, {
            "external_reference": "INITIAL-LOT-STALE",
            "warehouse_external_id": "WH-001",
            "lines": [{
                "product_external_id": "AGRI-LOT", "lot_external_id": "LOT-STALE",
                "quantity": 2000, "unit": "kg",
            }],
        })
        record = self.env["cool_agristock.inventory.import"].sudo().browse(self._body(response)["import_id"])
        lot = self.env["stock.lot"].sudo().browse(record.line_ids.lot_id.id)

        self.env["stock.quant"]._update_available_quantity(
            self.lot_tracked_product, self.warehouse.lot_stock_id, 500, lot_id=lot,
        )

        manager_group = self.env.ref("stock.group_stock_manager")
        manager_user = self.env["res.users"].create({
            "name": "Phase F Inventory Manager", "login": "cool_agristock_phasef_manager",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id, manager_group.id])],
        })
        record.with_user(manager_user).action_approve()
        self.assertEqual(record.state, "stale")
        self.assertEqual(record.line_ids.current_odoo_quantity, 500.0)

    # -- Receipt integration -------------------------------------------------

    def test_receipt_with_valid_lot(self):
        self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-RECEIPT"))
        create_resp = self._create_receipt(self.lot_tracked_product, 300)
        receipt_id = create_resp.json()["receipt_id"]

        response = self._validate_receipt(self.bound_raw_key, receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-LOT-%s" % self.lot_tracked_product.id,
            "received_quantities": [{
                "product_id": self.lot_tracked_product.id, "quantity": 300,
                "lot_external_id": "LOT-RECEIPT",
            }],
        })
        self.assertEqual(response.status_code, 200)
        picking = self.env["stock.picking"].browse(receipt_id)
        self.assertEqual(picking.state, "done")
        self.assertTrue(all(ml.lot_id.name == "COCOA-2026-001" for ml in picking.move_line_ids))

    def test_receipt_with_invalid_lot_rejected(self):
        create_resp = self._create_receipt(self.lot_tracked_product, 300)
        receipt_id = create_resp.json()["receipt_id"]

        response = self._validate_receipt(self.bound_raw_key, receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-LOT-%s" % self.lot_tracked_product.id,
            "received_quantities": [{
                "product_id": self.lot_tracked_product.id, "quantity": 300,
                "lot_external_id": "LOT-GHOST-RECEIPT",
            }],
        })
        self.assertEqual(response.status_code, 404)

    def test_receipt_tracked_product_without_lot_still_rejected(self):
        create_resp = self._create_receipt(self.lot_tracked_product, 50)
        receipt_id = create_resp.json()["receipt_id"]
        response = self._as_api_user(
            f"/cool_agristock/api/v1/receipts/{receipt_id}/validate", method="POST", json={
                "external_reference": "COOL_AGRISTOCK-RCPT-LOT-%s" % self.lot_tracked_product.id,
                "received_quantities": [{"product_id": self.lot_tracked_product.id, "quantity": 50}],
            },
        )
        self.assertEqual(response.status_code, 409)

    # -- Dispatch integration --------------------------------------------------

    def test_dispatch_with_valid_lot(self):
        lot_resp = self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-DISPATCH"))
        lot = self.env["stock.lot"].browse(self._body(lot_resp)["lot_id"])
        self.env["stock.quant"]._update_available_quantity(
            self.lot_tracked_product, self.warehouse.lot_stock_id, 1000, lot_id=lot,
        )

        create_resp = self._create_dispatch(self.lot_tracked_product, 400, "COOL_AGRISTOCK-DISP-LOT-1")
        dispatch_id = create_resp.json()["dispatch_id"]

        response = self._validate_dispatch(self.bound_raw_key, dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-LOT-1",
            "dispatched_quantities": [{
                "product_id": self.lot_tracked_product.id, "quantity": 400,
                "lot_external_id": "LOT-DISPATCH",
            }],
        })
        self.assertEqual(response.status_code, 200)
        picking = self.env["stock.picking"].browse(dispatch_id)
        self.assertEqual(picking.state, "done")

        # Scoped to the source warehouse location specifically -- the
        # dispatched 400 units now sit at the customer location instead,
        # so summing across *all* locations for this lot would net back
        # to the original 1000 (correct conservation, not a bug), which
        # isn't what this test is checking.
        remaining = sum(self.env["stock.quant"].search([
            ("product_id", "=", self.lot_tracked_product.id),
            ("lot_id", "=", lot.id),
            ("location_id", "=", self.warehouse.lot_stock_id.id),
        ]).mapped("quantity"))
        self.assertEqual(remaining, 600.0)

    def test_dispatch_insufficient_lot_stock_rejected(self):
        lot_resp = self._post_lot(self.bound_raw_key, self._lot_payload(external_id="LOT-SHORT"))
        lot = self.env["stock.lot"].browse(self._body(lot_resp)["lot_id"])
        self.env["stock.quant"]._update_available_quantity(
            self.lot_tracked_product, self.warehouse.lot_stock_id, 10, lot_id=lot,
        )

        create_resp = self._create_dispatch(self.lot_tracked_product, 400, "COOL_AGRISTOCK-DISP-LOT-2")
        dispatch_id = create_resp.json()["dispatch_id"]

        response = self._validate_dispatch(self.bound_raw_key, dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-LOT-2",
            "dispatched_quantities": [{
                "product_id": self.lot_tracked_product.id, "quantity": 400,
                "lot_external_id": "LOT-SHORT",
            }],
        })
        self.assertEqual(response.status_code, 409)

    def test_dispatch_with_invalid_lot_rejected(self):
        create_resp = self._create_dispatch(self.lot_tracked_product, 50, "COOL_AGRISTOCK-DISP-LOT-3")
        dispatch_id = create_resp.json()["dispatch_id"]
        response = self._validate_dispatch(self.bound_raw_key, dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-LOT-3",
            "dispatched_quantities": [{
                "product_id": self.lot_tracked_product.id, "quantity": 50,
                "lot_external_id": "LOT-GHOST-DISPATCH",
            }],
        })
        self.assertEqual(response.status_code, 404)

    # -- Backward compatibility -------------------------------------------------

    def test_existing_untracked_receipt_dispatch_unaffected(self):
        response = self._as_api_user("/cool_agristock/api/v1/receipts", method="POST", json={
            "external_reference": "COOL_AGRISTOCK-RCPT-PHASE-F-CHECK",
            "warehouse_id": self.warehouse.id,
            "supplier_id": self.partner.id,
            "products": [{"product_id": self.product.id, "quantity": 10}],
        })
        self.assertEqual(response.status_code, 201)

    def test_existing_endpoints_unaffected(self):
        response = self.url_open(
            "/cool_agristock/api/v1/products", json={"external_id": "PHASE-F-CHECK", "name": "Still Works"},
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 201)
