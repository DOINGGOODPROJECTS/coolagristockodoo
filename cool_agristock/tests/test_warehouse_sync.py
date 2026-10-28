import datetime
import json

from odoo import fields
from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockWarehouseSync(CoolAgristockApiCommon):
    """POST/PATCH /cool_agristock/api/v1/warehouses: creation, native location
    generation, updates, duplicate prevention, and the security matrix.
    Mirrors test_product_sync.py's structure and fixture reasoning."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        internal_group = cls.env.ref("base.group_user")
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")

        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Primary WMS",
            "code": "primary_wms",
            "company_id": cls.env.company.id,
        })

        ApiKey = cls.env["cool_agristock.api.key"].with_user(cls.admin_user)
        cls.bound_raw_key, cls.bound_key_record = ApiKey.generate_key(
            name="Bound WMS Key", company=cls.env.company, external_system=cls.external_system,
        )

        # Dedicated company with no bound key anywhere -- see
        # test_product_sync.py's identical reasoning: "unbound" is a
        # property of a company's whole shared integration identity, not
        # of one individual named key.
        cls.unbound_only_company = cls.env["res.company"].create({
            "name": "Phase C Unbound-Only Company",
        })
        cls.unbound_only_admin_user = cls.env["res.users"].create({
            "name": "Phase C Unbound-Only Admin",
            "login": "cool_agristock_phasec_unbound_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.unbound_only_company.id])],
            "company_id": cls.unbound_only_company.id,
        })
        cls.unbound_raw_key, cls.unbound_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.unbound_only_admin_user
        ).generate_key(name="Unbound Key", company=cls.unbound_only_company)

        cls.other_company = cls.env["res.company"].create({"name": "Phase C Other Company"})
        cls.other_admin_user = cls.env["res.users"].create({
            "name": "Phase C Other Company Admin",
            "login": "cool_agristock_phasec_other_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.other_company.id])],
            "company_id": cls.other_company.id,
        })
        cls.other_external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Other Co WMS",
            "code": "primary_wms",
            "company_id": cls.other_company.id,
        })
        cls.other_raw_key, cls.other_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.other_admin_user
        ).generate_key(name="Other Co Key", company=cls.other_company, external_system=cls.other_external_system)

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _post(self, key, data):
        return self.url_open(
            "/cool_agristock/api/v1/warehouses", json=data, headers=self._headers(key),
        )

    def _patch(self, key, external_id, data):
        return self.url_open(
            f"/cool_agristock/api/v1/warehouses/{external_id}",
            json=data, headers=self._headers(key), method="PATCH",
        )

    def _body(self, response):
        return json.loads(response.content)

    # -- Warehouse creation ---------------------------------------------

    def test_create_warehouse(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "WH-001", "name": "Anyama Warehouse", "code": "ANY",
        })
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        self.assertEqual(body["code"], "ANY")

    def test_native_stock_location_generation(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "WH-LOC", "name": "Location Check Warehouse", "code": "LOCW",
        })
        body = self._body(response)
        warehouse = self.env["stock.warehouse"].sudo().browse(body["warehouse_id"])
        # Odoo's own create() override is what populates these -- not any
        # code in this module -- confirming the native workflow ran.
        self.assertTrue(warehouse.view_location_id)
        self.assertTrue(warehouse.lot_stock_id)
        self.assertTrue(warehouse.in_type_id)
        self.assertTrue(warehouse.out_type_id)
        self.assertEqual(warehouse.view_location_id.company_id, warehouse.company_id)

    def test_missing_warehouse_name(self):
        response = self._post(self.bound_raw_key, {"external_id": "WH-002", "code": "NON"})
        self.assertEqual(response.status_code, 400)

    def test_missing_external_id(self):
        response = self._post(self.bound_raw_key, {"name": "No External Id", "code": "NEI"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_warehouse_code_too_long(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "WH-003", "name": "Too Long Code", "code": "TOOLONG",
        })
        self.assertEqual(response.status_code, 422)

    def test_duplicate_warehouse_code_rejected(self):
        self._post(self.bound_raw_key, {
            "external_id": "WH-CODE-A", "name": "Code Owner", "code": "DUP",
        })
        response = self._post(self.bound_raw_key, {
            "external_id": "WH-CODE-B", "name": "Code Claimer", "code": "DUP",
        })
        self.assertEqual(response.status_code, 409)

    def test_unsupported_field_rejected(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "WH-004", "name": "Has Route", "code": "RTE",
            "route_ids": [1, 2, 3],
        })
        self.assertEqual(response.status_code, 400)

    # -- Warehouse updates ------------------------------------------------

    def test_update_warehouse(self):
        create_response = self._post(self.bound_raw_key, {
            "external_id": "WH-UPDATE", "name": "Original Name", "code": "ORIG",
        })
        self.assertEqual(create_response.status_code, 201)

        update_response = self._patch(self.bound_raw_key, "WH-UPDATE", {"name": "Updated Name"})
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(self._body(update_response)["name"], "Updated Name")

    def test_repeated_patch_idempotent_update(self):
        self._post(self.bound_raw_key, {
            "external_id": "WH-REPEAT-PATCH", "name": "First", "code": "RPT",
        })
        first = self._patch(self.bound_raw_key, "WH-REPEAT-PATCH", {"name": "Second"})
        second = self._patch(self.bound_raw_key, "WH-REPEAT-PATCH", {"name": "Second"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

    def test_code_cannot_be_changed_via_patch(self):
        self._post(self.bound_raw_key, {
            "external_id": "WH-CODE-LOCK", "name": "Locked Code", "code": "LCK",
        })
        response = self._patch(self.bound_raw_key, "WH-CODE-LOCK", {"code": "NEW"})
        self.assertEqual(response.status_code, 400)

    def test_update_unknown_external_id_returns_404(self):
        response = self._patch(self.bound_raw_key, "WH-NEVER-CREATED", {"name": "Doesn't Matter"})
        self.assertEqual(response.status_code, 404)

    def test_update_preserves_operational_configuration(self):
        create_response = self._post(self.bound_raw_key, {
            "external_id": "WH-PRESERVE", "name": "Preserve Me", "code": "PRE",
        })
        warehouse_id = self._body(create_response)["warehouse_id"]
        warehouse = self.env["stock.warehouse"].sudo().browse(warehouse_id)
        original_in_type = warehouse.in_type_id
        original_lot_stock = warehouse.lot_stock_id

        self._patch(self.bound_raw_key, "WH-PRESERVE", {"name": "Preserve Me Updated"})

        warehouse.invalidate_recordset()
        self.assertEqual(warehouse.in_type_id, original_in_type)
        self.assertEqual(warehouse.lot_stock_id, original_lot_stock)

    # -- Duplicate / atomicity --------------------------------------------

    def test_duplicate_post_no_duplicate_warehouse(self):
        first = self._post(self.bound_raw_key, {
            "external_id": "WH-DUPLICATE", "name": "First Attempt", "code": "DP1",
        })
        self.assertEqual(first.status_code, 201)
        first_id = self._body(first).get("warehouse_id")

        second = self._post(self.bound_raw_key, {
            "external_id": "WH-DUPLICATE", "name": "Second Attempt", "code": "DP2",
        })
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self._body(second).get("warehouse_id"), first_id)

        count = self.env["stock.warehouse"].sudo().search_count([
            ("name", "in", ["First Attempt", "Second Attempt"]),
        ])
        self.assertEqual(count, 1)

    def test_atomic_creation_and_mapping(self):
        # Reuses the exact concurrency-proof pattern from
        # test_external_id_mapping.py: bypass the service's own
        # pre-check to force the database constraint itself to reject a
        # duplicate, proving the DB -- not just app logic -- enforces it.
        Mapping = self.env["cool_agristock.external.id.mapping"].sudo()
        warehouse = self.env["stock.warehouse"].sudo().create({
            "name": "Atomicity Check", "code": "ATC", "company_id": self.env.company.id,
        })
        Mapping.create({
            "company_id": self.env.company.id,
            "external_system_id": self.external_system.id,
            "res_model": "stock.warehouse",
            "external_id": "WH-ATOMIC",
            "res_id": warehouse.id,
        })
        other_warehouse = self.env["stock.warehouse"].sudo().create({
            "name": "Atomicity Check 2", "code": "AT2", "company_id": self.env.company.id,
        })
        import psycopg2
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                Mapping.create({
                    "company_id": self.env.company.id,
                    "external_system_id": self.external_system.id,
                    "res_model": "stock.warehouse",
                    "external_id": "WH-ATOMIC",
                    "res_id": other_warehouse.id,
                })

    # -- Security / authentication ------------------------------------------

    def test_missing_api_key(self):
        response = self._post(None, {"external_id": "WH-005", "name": "No Key", "code": "NOK"})
        self.assertEqual(response.status_code, 401)

    def test_invalid_api_key(self):
        response = self._post("not-a-real-key", {"external_id": "WH-006", "name": "Bad Key", "code": "BAD"})
        self.assertEqual(response.status_code, 401)

    def test_revoked_api_key_rejected(self):
        raw_key, record = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="To Be Revoked", company=self.env.company, external_system=self.external_system,
        )
        record.with_user(self.admin_user).action_revoke()
        response = self._post(raw_key, {"external_id": "WH-007", "name": "Revoked", "code": "REV"})
        self.assertEqual(response.status_code, 401)

    def test_expired_api_key_rejected(self):
        past = fields.Datetime.now() - datetime.timedelta(days=1)
        raw_key, record = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="Expired Key", company=self.env.company,
            expiration_date=fields.Datetime.now() + datetime.timedelta(seconds=1),
            external_system=self.external_system,
        )
        self.env.cr.execute(
            "UPDATE res_users_apikeys SET expiration_date = %s WHERE id = %s",
            (past, record.apikey_id.id),
        )
        response = self._post(raw_key, {"external_id": "WH-008", "name": "Expired", "code": "EXP"})
        self.assertEqual(response.status_code, 401)

    def test_unbound_key_rejected(self):
        response = self._post(self.unbound_raw_key, {
            "external_id": "WH-009", "name": "Unbound", "code": "UNB",
        })
        self.assertEqual(response.status_code, 403)

    def test_unbound_key_still_works_for_existing_get_endpoint(self):
        response = self.url_open(
            "/cool_agristock/api/v1/warehouses", headers=self._headers(self.unbound_raw_key),
        )
        self.assertEqual(response.status_code, 200)

    def test_inactive_external_system_rejected(self):
        self.external_system.sudo().active = False
        try:
            response = self._post(self.bound_raw_key, {
                "external_id": "WH-010", "name": "Inactive System", "code": "INA",
            })
            self.assertEqual(response.status_code, 403)
        finally:
            self.external_system.sudo().active = True

    def test_cross_company_warehouse_creation_isolated(self):
        response_a = self._post(self.bound_raw_key, {
            "external_id": "WH-CROSS", "name": "Company A WH", "code": "CRA",
        })
        response_b = self._post(self.other_raw_key, {
            "external_id": "WH-CROSS", "name": "Company B WH", "code": "CRB",
        })
        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 201)
        self.assertNotEqual(
            self._body(response_a)["warehouse_id"], self._body(response_b)["warehouse_id"],
        )

    def test_cross_company_update_rejected(self):
        self._post(self.bound_raw_key, {
            "external_id": "WH-CROSS-UPDATE", "name": "Mine", "code": "MIN",
        })
        response = self._patch(self.other_raw_key, "WH-CROSS-UPDATE", {"name": "Hijacked"})
        self.assertEqual(response.status_code, 404)

    # -- Existing functionality compatibility --------------------------------

    def test_existing_get_warehouses_endpoint_unchanged(self):
        response = self.url_open(
            "/cool_agristock/api/v1/warehouses", headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 200)
        body = self._body(response)
        self.assertIn("warehouses", body)

    def test_existing_product_sync_unaffected(self):
        response = self.url_open(
            "/cool_agristock/api/v1/products", json={"external_id": "WH-PHASE-B-CHECK", "name": "Still Works"},
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 201)

    def test_existing_receipt_dispatch_endpoints_unaffected(self):
        response = self.url_open(
            "/cool_agristock/api/v1/receipts",
            json={
                "external_reference": "COOL_AGRISTOCK-RCPT-WHPHASE-1",
                "warehouse_id": self.warehouse.id,
                "supplier_id": self.partner.id,
                "products": [{"product_id": self.product.id, "quantity": 10}],
            },
            headers=self._auth_headers(self.api_key),
        )
        self.assertEqual(response.status_code, 201)
