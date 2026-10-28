import json

import psycopg2
from odoo.tests.common import tagged
from odoo.exceptions import AccessError

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockInventoryImport(CoolAgristockApiCommon):
    """POST /cool_agristock/api/v1/inventory-adjustments: staged inventory
    import, reconciliation, human review, stale-data detection,
    idempotency, lot/serial rejection, and the security matrix."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        internal_group = cls.env.ref("base.group_user")
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")
        manager_group = cls.env.ref("stock.group_stock_manager")

        # CoolAgristockApiCommon's shared fixtures default to Odoo's base
        # "Units" UOM -- this suite's payloads use "kg" throughout
        # (matching the task's own example payloads), so the fixture
        # products must actually be kg-based or every request would be
        # correctly rejected as an incompatible-unit mismatch (exactly
        # the check Phase E's UOM compatibility logic exists to enforce).
        kg = cls.env.ref("uom.product_uom_kgm")
        cls.product.uom_id = kg
        cls.lot_tracked_product.uom_id = kg
        cls.serial_tracked_product.uom_id = kg

        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Primary WMS", "code": "primary_wms_e",
            "company_id": cls.env.company.id,
            "allow_automatic_inventory_adjustments": True,
            "max_auto_inventory_delta": 1000,
        })

        ApiKey = cls.env["cool_agristock.api.key"].with_user(cls.admin_user)
        cls.bound_raw_key, cls.bound_key_record = ApiKey.generate_key(
            name="Bound WMS Key E", company=cls.env.company, external_system=cls.external_system,
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

        cls.inventory_manager_user = cls.env["res.users"].create({
            "name": "Cool Agristock Inventory Manager", "login": "cool_agristock_inventory_manager",
            "group_ids": [(6, 0, [internal_group.id, manager_group.id])],
            "company_ids": [(6, 0, [cls.env.company.id])], "company_id": cls.env.company.id,
        })

        cls.unbound_only_company = cls.env["res.company"].create({
            "name": "Phase E Unbound-Only Company",
        })
        cls.unbound_only_admin_user = cls.env["res.users"].create({
            "name": "Phase E Unbound-Only Admin", "login": "cool_agristock_phasee_unbound_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.unbound_only_company.id])],
            "company_id": cls.unbound_only_company.id,
        })
        cls.unbound_raw_key, cls.unbound_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.unbound_only_admin_user
        ).generate_key(name="Unbound Key E", company=cls.unbound_only_company)

        cls.other_company = cls.env["res.company"].create({"name": "Phase E Other Company"})
        cls.other_admin_user = cls.env["res.users"].create({
            "name": "Phase E Other Company Admin", "login": "cool_agristock_phasee_other_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.other_company.id])], "company_id": cls.other_company.id,
        })
        cls.other_external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Other Co WMS", "code": "primary_wms_e", "company_id": cls.other_company.id,
        })
        cls.other_raw_key, cls.other_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.other_admin_user
        ).generate_key(
            name="Other Co Key E", company=cls.other_company, external_system=cls.other_external_system,
        )

        # A second external system within the SAME company -- for
        # cross-system (not cross-company) isolation.
        cls.second_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Second WMS Same Co", "code": "second_wms_e", "company_id": cls.env.company.id,
        })
        cls.second_system_raw_key, cls.second_system_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.admin_user
        ).generate_key(
            name="Second System Key E", company=cls.env.company, external_system=cls.second_system,
        )

    # -- helpers ----------------------------------------------------------

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _post(self, key, data):
        return self.url_open(
            "/cool_agristock/api/v1/inventory-adjustments", json=data, headers=self._headers(key),
        )

    def _post_auto(self, key, data):
        return self.url_open(
            "/cool_agristock/api/v1/inventory-adjustments/apply",
            json=data, headers=self._headers(key),
        )

    def _body(self, response):
        return json.loads(response.content)

    def _payload(self, reference, lines, warehouse_external_id="WH-001"):
        return {
            "external_reference": reference,
            "warehouse_external_id": warehouse_external_id,
            "lines": lines,
        }

    def _line(self, product_external_id="AGRI-001", quantity=5000, unit="kg"):
        return {
            "product_external_id": product_external_id,
            "quantity": quantity,
            "unit": unit,
        }

    # -- 1. Valid inventory import -----------------------------------------

    def test_valid_inventory_import(self):
        response = self._post(self.bound_raw_key, self._payload("INITIAL-2026-001", [self._line()]))
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        self.assertEqual(body["state"], "pending_review")
        record = self.env["cool_agristock.inventory.import"].sudo().browse(body["import_id"])
        self.assertEqual(record.external_reference, "INITIAL-2026-001")
        self.assertEqual(record.warehouse_id, self.warehouse)
        self.assertEqual(record.location_id, self.warehouse.lot_stock_id)

    def test_auto_apply_adjusts_stock_and_records_audit(self):
        response = self._post_auto(
            self.bound_raw_key,
            self._payload("AUTO-ADJUST-001", [self._line(quantity=12)]),
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = self._body(response)
        self.assertEqual(body["state"], "applied")
        record = self.env["cool_agristock.inventory.import"].sudo().browse(body["import_id"])
        self.assertEqual(record.applied_by, self.bound_key_record.integration_user_id)
        self.assertTrue(record.applied_at)
        self.assertEqual(
            self.env["stock.quant"].sudo()._get_available_quantity(
                self.product, self.warehouse.lot_stock_id,
            ),
            12,
        )

    def test_auto_apply_updates_existing_stock_with_native_moves(self):
        Quant = self.env["stock.quant"].sudo()
        Quant._update_available_quantity(self.product, self.warehouse.lot_stock_id, 7)
        response = self._post_auto(
            self.bound_raw_key,
            self._payload("AUTO-EXISTING", [self._line(quantity=12)]),
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Quant._get_available_quantity(
            self.product, self.warehouse.lot_stock_id), 12)
        moves = self.env["stock.move"].search([
            ("product_id", "=", self.product.id), ("state", "=", "done"),
            ("is_inventory", "=", True),
        ])
        self.assertTrue(moves, "Automatic adjustments must leave native stock move history")

    def test_auto_apply_preserves_pending_manual_count(self):
        Quant = self.env["stock.quant"].sudo()
        Quant._update_available_quantity(self.product, self.warehouse.lot_stock_id, 7)
        quant = Quant.search([("product_id", "=", self.product.id),
                              ("location_id", "=", self.warehouse.lot_stock_id.id)])
        quant.with_context(inventory_mode=True).inventory_quantity = 9
        response = self._post_auto(
            self.bound_raw_key,
            self._payload("AUTO-MANUAL-CONFLICT", [self._line(quantity=12)]),
        )
        self.assertEqual(response.status_code, 409, response.content)
        quant.invalidate_recordset()
        self.assertEqual(quant.quantity, 7)
        self.assertEqual(quant.inventory_quantity, 9)

    def test_auto_apply_requires_wms_opt_in(self):
        self.external_system.allow_automatic_inventory_adjustments = False
        response = self._post_auto(self.bound_raw_key, self._payload(
            "AUTO-NO-OPT-IN", [self._line(quantity=12)]))
        self.assertEqual(response.status_code, 403, response.content)

    def test_non_finite_count_rejected(self):
        response = self.url_open(
            "/cool_agristock/api/v1/inventory-adjustments/apply",
            data=json.dumps(self._payload("AUTO-NAN", [self._line(quantity=float("nan"))])),
            headers={"Authorization": "Bearer " + self.bound_raw_key,
                     "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_auto_apply_retry_is_idempotent(self):
        payload = self._payload("AUTO-ADJUST-RETRY", [self._line(quantity=15)])
        first = self._post_auto(self.bound_raw_key, payload)
        second = self._post_auto(self.bound_raw_key, payload)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(self._body(second)["state"], "applied")
        self.assertEqual(
            self.env["stock.quant"].sudo()._get_available_quantity(
                self.product, self.warehouse.lot_stock_id,
            ),
            15,
        )

    def test_auto_apply_rejects_reference_already_staged(self):
        payload = self._payload("AUTO-ADJUST-STAGED", [self._line(quantity=8)])
        staged = self._post(self.bound_raw_key, payload)
        attempted = self._post_auto(self.bound_raw_key, payload)
        self.assertEqual(staged.status_code, 201)
        self.assertEqual(attempted.status_code, 409)
        self.assertEqual(
            self.env["stock.quant"].sudo()._get_available_quantity(
                self.product, self.warehouse.lot_stock_id,
            ),
            0,
        )

    def test_auto_apply_rejects_variance_above_configured_limit(self):
        response = self._post_auto(
            self.bound_raw_key,
            self._payload("AUTO-ADJUST-OVER-LIMIT", [self._line(quantity=1001)]),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.env["stock.quant"].sudo()._get_available_quantity(
                self.product, self.warehouse.lot_stock_id,
            ),
            0,
        )

    # -- 2. Multiple import lines -------------------------------------------

    def test_multiple_import_lines(self):
        second_product = self.env["product.product"].sudo().create({
            "name": "Cool Agristock Second Product", "type": "consu", "is_storable": True,
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        self.env["cool_agristock.external.id.mapping"].sudo().create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "res_model": "product.product", "external_id": "AGRI-002", "res_id": second_product.id,
        })
        response = self._post(self.bound_raw_key, self._payload("INITIAL-2026-002", [
            self._line("AGRI-001", 5000, "kg"),
            self._line("AGRI-002", 3000, "kg"),
        ]))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self._body(response)["lines"]), 2)

    # -- 3/4. Unknown product / warehouse ------------------------------------

    def test_unknown_product_rejected(self):
        response = self._post(self.bound_raw_key, self._payload("INITIAL-UNKNOWN-PROD", [
            self._line("AGRI-DOES-NOT-EXIST"),
        ]))
        self.assertEqual(response.status_code, 404)

    def test_unknown_warehouse_rejected(self):
        response = self._post(
            self.bound_raw_key,
            self._payload("INITIAL-UNKNOWN-WH", [self._line()], warehouse_external_id="WH-DOES-NOT-EXIST"),
        )
        self.assertEqual(response.status_code, 404)

    # -- 5/6. Units -----------------------------------------------------------

    def test_invalid_unit_rejected(self):
        response = self._post(self.bound_raw_key, self._payload(
            "INITIAL-BAD-UNIT", [self._line(unit="furlongs")],
        ))
        self.assertEqual(response.status_code, 400)

    def test_incompatible_unit_category_rejected(self):
        # "l" (volume) is not convertible to a kg-based product's unit
        # (mass) -- this must be refused, not silently miscomputed.
        response = self._post(self.bound_raw_key, self._payload(
            "INITIAL-INCOMPATIBLE-UNIT", [self._line(unit="l")],
        ))
        self.assertEqual(response.status_code, 422)

    # -- 7. Negative quantity ---------------------------------------------

    def test_negative_quantity_rejected(self):
        response = self._post(self.bound_raw_key, self._payload(
            "INITIAL-NEGATIVE", [self._line(quantity=-5)],
        ))
        self.assertEqual(response.status_code, 400)

    # -- 8/9. Idempotency and conflicting duplicates -------------------------

    def test_duplicate_identical_request_is_idempotent(self):
        first = self._post(self.bound_raw_key, self._payload("INITIAL-DUP", [self._line()]))
        self.assertEqual(first.status_code, 201)
        first_id = self._body(first)["import_id"]

        second = self._post(self.bound_raw_key, self._payload("INITIAL-DUP", [self._line()]))
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self._body(second)["import_id"], first_id)
        self.assertEqual(
            self.env["cool_agristock.inventory.import"].sudo().search_count(
                [("external_reference", "=", "INITIAL-DUP")]
            ),
            1,
        )

    def test_duplicate_conflicting_request_rejected(self):
        first = self._post(self.bound_raw_key, self._payload("INITIAL-CONFLICT", [self._line(quantity=5000)]))
        self.assertEqual(first.status_code, 201)

        second = self._post(self.bound_raw_key, self._payload("INITIAL-CONFLICT", [self._line(quantity=9999)]))
        self.assertEqual(second.status_code, 409)

    # -- 10. Concurrent duplicate submissions --------------------------------

    def test_concurrent_duplicate_enforced_by_database(self):
        Import = self.env["cool_agristock.inventory.import"].sudo()
        Import.create({
            "company_id": self.env.company.id,
            "external_system_id": self.external_system.id,
            "external_reference": "INITIAL-RACE",
            "warehouse_id": self.warehouse.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "request_hash": "hash-a",
            "submitted_by": self.env.user.id,
        })
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                Import.create({
                    "company_id": self.env.company.id,
                    "external_system_id": self.external_system.id,
                    "external_reference": "INITIAL-RACE",
                    "warehouse_id": self.warehouse.id,
                    "location_id": self.warehouse.lot_stock_id.id,
                    "request_hash": "hash-b",
                    "submitted_by": self.env.user.id,
                })

    # -- 11/12. Cross-company / cross-system isolation -----------------------

    def test_cross_company_access_rejected(self):
        response = self._post(self.other_raw_key, self._payload("INITIAL-CROSS-CO", [self._line()]))
        # The other company's key cannot even resolve "WH-001" -- it was
        # mapped under a different company.
        self.assertEqual(response.status_code, 404)

    def test_cross_system_access_rejected(self):
        response = self._post(self.second_system_raw_key, self._payload("INITIAL-CROSS-SYS", [self._line()]))
        # Same company, different external system -- the mapping is
        # scoped to the *first* system, so the second system cannot see it.
        self.assertEqual(response.status_code, 404)

    # -- 13/14. Unbound key / inactive external system -----------------------

    def test_unbound_key_rejected(self):
        response = self._post(self.unbound_raw_key, self._payload("INITIAL-UNBOUND", [self._line()]))
        self.assertEqual(response.status_code, 403)

    def test_inactive_external_system_rejected(self):
        self.external_system.sudo().active = False
        try:
            response = self._post(self.bound_raw_key, self._payload("INITIAL-INACTIVE", [self._line()]))
            self.assertEqual(response.status_code, 403)
        finally:
            self.external_system.sudo().active = True

    # -- 15/16. Lot / serial tracking rejection ------------------------------

    def test_lot_tracked_product_rejected(self):
        response = self._post(self.bound_raw_key, self._payload(
            "INITIAL-LOT", [self._line(product_external_id="AGRI-LOT")],
        ))
        self.assertEqual(response.status_code, 422)

    def test_serial_tracked_product_rejected(self):
        response = self._post(self.bound_raw_key, self._payload(
            "INITIAL-SERIAL", [self._line(product_external_id="AGRI-SERIAL")],
        ))
        self.assertEqual(response.status_code, 422)

    # -- 17. Multiple-location ambiguity --------------------------------------

    def test_only_lot_stock_id_is_ever_considered(self):
        # Put real stock in a *different* internal location under the
        # same warehouse, and confirm the import's reconciliation is
        # based only on warehouse.lot_stock_id -- never arbitrarily
        # distributed across, or summed with, another location.
        other_location = self.env["stock.location"].sudo().create({
            "name": "Phase E Side Shelf",
            "location_id": self.warehouse.view_location_id.id,
            "usage": "internal",
            "company_id": self.env.company.id,
        })
        self.env["stock.quant"].sudo()._update_available_quantity(
            self.product, other_location, 999999,
        )
        response = self._post(self.bound_raw_key, self._payload("INITIAL-NO-AMBIGUITY", [self._line()]))
        self.assertEqual(response.status_code, 201)
        record = self.env["cool_agristock.inventory.import"].sudo().browse(self._body(response)["import_id"])
        self.assertEqual(record.location_id, self.warehouse.lot_stock_id)
        self.assertEqual(record.line_ids.current_odoo_quantity, 0.0)

    # -- 18/19/20. Reconciliation arithmetic ----------------------------------

    def test_existing_stock_difference_calculated(self):
        self.env["stock.quant"].sudo()._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 2000,
        )
        response = self._post(self.bound_raw_key, self._payload("INITIAL-EXISTING-STOCK", [
            self._line(quantity=5000),
        ]))
        self.assertEqual(response.status_code, 201)
        line = self._body(response)["lines"][0]
        self.assertEqual(line["current_odoo_quantity"], 2000.0)
        self.assertEqual(line["reported_quantity"], 5000.0)
        self.assertEqual(line["proposed_difference"], 3000.0)

    def test_zero_existing_stock(self):
        response = self._post(self.bound_raw_key, self._payload("INITIAL-ZERO-STOCK", [
            self._line(quantity=1234),
        ]))
        line = self._body(response)["lines"][0]
        self.assertEqual(line["current_odoo_quantity"], 0.0)
        self.assertEqual(line["proposed_difference"], 1234.0)

    # -- 21. Stale data detection ---------------------------------------------

    def test_stale_data_detected_on_approve(self):
        response = self._post(self.bound_raw_key, self._payload("INITIAL-STALE", [self._line(quantity=5000)]))
        record = self.env["cool_agristock.inventory.import"].sudo().browse(self._body(response)["import_id"])
        self.assertEqual(record.line_ids.current_odoo_quantity, 0.0)

        # Stock changes after submission, before review.
        self.env["stock.quant"].sudo()._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 2500,
        )

        record.with_user(self.inventory_manager_user).action_approve()
        self.assertEqual(record.state, "stale")
        self.assertEqual(record.line_ids.current_odoo_quantity, 2500.0)
        self.assertEqual(record.line_ids.proposed_difference, 2500.0)

        # A second, informed approval now succeeds -- the reviewer has
        # seen the refreshed numbers.
        record.with_user(self.inventory_manager_user).action_approve()
        self.assertEqual(record.state, "approved")

    # -- 22. Unauthorized approval ---------------------------------------------

    def test_unauthorized_approval_rejected(self):
        response = self._post(self.bound_raw_key, self._payload("INITIAL-UNAUTH-APPROVE", [self._line()]))
        record = self.env["cool_agristock.inventory.import"].sudo().browse(self._body(response)["import_id"])
        with self.assertRaises(AccessError):
            record.with_user(self.plain_user).action_approve()

    # -- 23. Import rejection ---------------------------------------------------

    def test_import_rejection(self):
        response = self._post(self.bound_raw_key, self._payload("INITIAL-REJECT", [self._line()]))
        record = self.env["cool_agristock.inventory.import"].sudo().browse(self._body(response)["import_id"])
        record.with_user(self.inventory_manager_user).action_reject()
        self.assertEqual(record.state, "rejected")

    # -- 24. No automatic stock changes -----------------------------------------

    def test_no_automatic_stock_change(self):
        self.env["stock.quant"].sudo()._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 2000,
        )

        def _current_qty():
            return sum(self.env["stock.quant"].sudo().search([
                ("product_id", "=", self.product.id),
                ("location_id", "=", self.warehouse.lot_stock_id.id),
            ]).mapped("quantity"))

        before = _current_qty()
        response = self._post(self.bound_raw_key, self._payload("INITIAL-NO-AUTO-CHANGE", [
            self._line(quantity=5000),
        ]))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(_current_qty(), before)

        record = self.env["cool_agristock.inventory.import"].sudo().browse(self._body(response)["import_id"])
        record.with_user(self.inventory_manager_user).action_approve()
        self.assertEqual(record.state, "approved")
        self.assertEqual(_current_qty(), before)

    # -- 25. Existing API compatibility -------------------------------------------

    def test_existing_endpoints_unaffected(self):
        response = self.url_open(
            "/cool_agristock/api/v1/products",
            json={"external_id": "PHASE-E-CHECK", "name": "Still Works"},
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 201)

    # -- Field allow-list ---------------------------------------------------------

    def test_unsupported_top_level_field_rejected(self):
        payload = self._payload("INITIAL-BAD-FIELD", [self._line()])
        payload["force_apply"] = True
        response = self._post(self.bound_raw_key, payload)
        self.assertEqual(response.status_code, 400)

    def test_unsupported_line_field_rejected(self):
        payload = self._payload("INITIAL-BAD-LINE-FIELD", [
            {"product_external_id": "AGRI-001", "quantity": 100, "unit": "kg", "lot": "LOT-1"},
        ])
        response = self._post(self.bound_raw_key, payload)
        self.assertEqual(response.status_code, 400)
