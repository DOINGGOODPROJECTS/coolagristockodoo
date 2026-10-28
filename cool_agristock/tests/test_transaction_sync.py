import json

import psycopg2
from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockTransactionSync(CoolAgristockApiCommon):
    """WMS-first POST/GET /cool_agristock/api/v1/receipts and /dispatches
    (Phase G): transaction identity, idempotency, UOM/lot resolution,
    status retrieval, and the full security matrix. Legacy numeric-ID
    behavior is asserted unchanged throughout."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        internal_group = cls.env.ref("base.group_user")
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")

        kg = cls.env.ref("uom.product_uom_kgm")
        cls.product.uom_id = kg
        cls.lot_tracked_product.uom_id = kg
        # serial_tracked_product is left at its default "Units" UOM --
        # this suite's serial tests send "unit": "unit" to match.

        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Primary WMS", "code": "primary_wms_g", "company_id": cls.env.company.id,
        })

        ApiKey = cls.env["cool_agristock.api.key"].with_user(cls.admin_user)
        cls.bound_raw_key, cls.bound_key_record = ApiKey.generate_key(
            name="Bound WMS Key G", company=cls.env.company, external_system=cls.external_system,
        )

        Mapping = cls.env["cool_agristock.external.id.mapping"].sudo()
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "stock.warehouse", "external_id": "WH-001", "res_id": cls.warehouse.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "product.product", "external_id": "PROD-001", "res_id": cls.product.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "product.product", "external_id": "PROD-LOT", "res_id": cls.lot_tracked_product.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "product.product", "external_id": "PROD-SERIAL", "res_id": cls.serial_tracked_product.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "res.partner", "external_id": "SUP-001", "res_id": cls.partner.id,
        })

        cls.lot = cls.env["stock.lot"].create({
            "name": "LOT-G-0001", "product_id": cls.lot_tracked_product.id,
            "company_id": cls.env.company.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "stock.lot", "external_id": "LOT-001", "res_id": cls.lot.id,
        })
        cls.serial_lot = cls.env["stock.lot"].create({
            "name": "SERIAL-G-0001", "product_id": cls.serial_tracked_product.id,
            "company_id": cls.env.company.id,
        })
        Mapping.create({
            "company_id": cls.env.company.id, "external_system_id": cls.external_system.id,
            "res_model": "stock.lot", "external_id": "SERIAL-001", "res_id": cls.serial_lot.id,
        })

        cls.unbound_only_company = cls.env["res.company"].create({
            "name": "Phase G Unbound-Only Company",
        })
        cls.unbound_only_admin_user = cls.env["res.users"].create({
            "name": "Phase G Unbound-Only Admin", "login": "cool_agristock_phaseg_unbound_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.unbound_only_company.id])],
            "company_id": cls.unbound_only_company.id,
        })
        cls.unbound_raw_key, cls.unbound_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.unbound_only_admin_user
        ).generate_key(name="Unbound Key G", company=cls.unbound_only_company)

        cls.other_company = cls.env["res.company"].create({"name": "Phase G Other Company"})
        cls.other_admin_user = cls.env["res.users"].create({
            "name": "Phase G Other Company Admin", "login": "cool_agristock_phaseg_other_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.other_company.id])], "company_id": cls.other_company.id,
        })
        cls.other_external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Other Co WMS", "code": "primary_wms_g", "company_id": cls.other_company.id,
        })
        cls.other_raw_key, cls.other_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.other_admin_user
        ).generate_key(
            name="Other Co Key G", company=cls.other_company, external_system=cls.other_external_system,
        )

        cls.second_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Second WMS Same Co", "code": "second_wms_g", "company_id": cls.env.company.id,
        })
        cls.second_system_raw_key, cls.second_system_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.admin_user
        ).generate_key(
            name="Second System Key G", company=cls.env.company, external_system=cls.second_system,
        )

    # -- helpers ----------------------------------------------------------

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _body(self, response):
        return json.loads(response.content)

    def _post_receipt(self, key, data):
        return self.url_open("/cool_agristock/api/v1/receipts", json=data, headers=self._headers(key))

    def _post_dispatch(self, key, data):
        return self.url_open("/cool_agristock/api/v1/dispatches", json=data, headers=self._headers(key))

    def _get_receipt(self, key, external_reference):
        return self.url_open(
            f"/cool_agristock/api/v1/receipts/{external_reference}", headers=self._headers(key),
        )

    def _get_dispatch(self, key, external_reference):
        return self.url_open(
            f"/cool_agristock/api/v1/dispatches/{external_reference}", headers=self._headers(key),
        )

    def _receipt_payload(self, reference, product_external_id="PROD-001", quantity=5000,
                          unit="kg", lot_external_id=None, supplier_external_id="SUP-001"):
        line = {"product_external_id": product_external_id, "quantity": quantity, "unit": unit}
        if lot_external_id:
            line["lot_external_id"] = lot_external_id
        return {
            "external_reference": reference,
            "warehouse_external_id": "WH-001",
            "supplier_external_id": supplier_external_id,
            "lines": [line],
        }

    def _dispatch_payload(self, reference, product_external_id="PROD-001", quantity=1500,
                           unit="kg", lot_external_id=None):
        line = {"product_external_id": product_external_id, "quantity": quantity, "unit": unit}
        if lot_external_id:
            line["lot_external_id"] = lot_external_id
        return {
            "external_reference": reference,
            "warehouse_external_id": "WH-001",
            "lines": [line],
        }

    # -- 1/2. Receipt / dispatch creation -------------------------------------

    def test_receipt_creation(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-001"))
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        self.assertEqual(body["state"], "draft")
        picking = self.env["stock.picking"].browse(body["receipt_id"])
        self.assertEqual(picking.origin, "WMS-REC-001")
        self.assertEqual(body["lines"][0]["product_id"], self.product.id)

    def test_dispatch_creation(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 5000,
        )
        response = self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-001"))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self._body(response)["state"], "draft")

    # -- 3/4. Duplicate (idempotent) -------------------------------------------

    def test_duplicate_receipt_identical_is_idempotent(self):
        first = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-DUP"))
        self.assertEqual(first.status_code, 201)
        first_id = self._body(first)["receipt_id"]
        second = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-DUP"))
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self._body(second)["receipt_id"], first_id)

    def test_duplicate_dispatch_identical_is_idempotent(self):
        first = self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-DUP"))
        self.assertEqual(first.status_code, 201)
        first_id = self._body(first)["dispatch_id"]
        second = self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-DUP"))
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self._body(second)["dispatch_id"], first_id)

    # -- 5/6. Conflicting reference ---------------------------------------------

    def test_conflicting_receipt_reference_rejected(self):
        self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-CONFLICT", quantity=5000))
        response = self._post_receipt(
            self.bound_raw_key, self._receipt_payload("WMS-REC-CONFLICT", quantity=9999),
        )
        self.assertEqual(response.status_code, 409)

    def test_conflicting_dispatch_reference_rejected(self):
        self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-CONFLICT", quantity=100))
        response = self._post_dispatch(
            self.bound_raw_key, self._dispatch_payload("WMS-DISP-CONFLICT", quantity=200),
        )
        self.assertEqual(response.status_code, 409)

    # -- 7. Concurrent requests -------------------------------------------------

    def test_concurrent_transaction_creation_enforced_by_database(self):
        Transaction = self.env["cool_agristock.wms.transaction"].sudo()
        picking = self.env["stock.picking"].sudo().create({
            "partner_id": self.partner.id,
            "picking_type_id": self.warehouse.in_type_id.id,
            "location_id": self.warehouse.in_type_id.default_location_src_id.id,
            "location_dest_id": self.warehouse.in_type_id.default_location_dest_id.id,
            "origin": "WMS-REC-RACE",
            "company_id": self.env.company.id,
        })
        Transaction.create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "transaction_type": "receipt", "external_reference": "WMS-REC-RACE",
            "request_hash": "hash-a", "picking_id": picking.id,
        })
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                Transaction.create({
                    "company_id": self.env.company.id, "external_system_id": self.external_system.id,
                    "transaction_type": "receipt", "external_reference": "WMS-REC-RACE",
                    "request_hash": "hash-b", "picking_id": picking.id,
                })

    # -- 8/9/10/11. Unknown references -----------------------------------------

    def test_unknown_product_rejected(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-UNKNOWN-PROD", product_external_id="PROD-GHOST",
        ))
        self.assertEqual(response.status_code, 404)

    def test_unknown_warehouse_rejected(self):
        payload = self._receipt_payload("WMS-REC-UNKNOWN-WH")
        payload["warehouse_external_id"] = "WH-GHOST"
        response = self._post_receipt(self.bound_raw_key, payload)
        self.assertEqual(response.status_code, 404)

    def test_unknown_supplier_rejected(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-UNKNOWN-SUP", supplier_external_id="SUP-GHOST",
        ))
        self.assertEqual(response.status_code, 404)

    def test_unknown_lot_rejected(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-UNKNOWN-LOT", product_external_id="PROD-LOT", lot_external_id="LOT-GHOST",
        ))
        self.assertEqual(response.status_code, 404)

    # -- 12/13. Invalid UOM / quantity --------------------------------------------

    def test_invalid_uom_rejected(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-BAD-UOM", unit="l",
        ))
        self.assertEqual(response.status_code, 422)

    def test_invalid_quantity_rejected(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-BAD-QTY", quantity=-5,
        ))
        self.assertEqual(response.status_code, 400)

    # -- 14/15. Cross-company / cross-system isolation ---------------------------

    def test_cross_company_isolation(self):
        response = self._post_receipt(self.other_raw_key, self._receipt_payload("WMS-REC-CROSS-CO"))
        self.assertEqual(response.status_code, 404)

    def test_cross_system_isolation(self):
        response = self._post_receipt(self.second_system_raw_key, self._receipt_payload("WMS-REC-CROSS-SYS"))
        self.assertEqual(response.status_code, 404)

    # -- 16/17. Unbound / revoked API key -----------------------------------------

    def test_unbound_key_rejected(self):
        response = self._post_receipt(self.unbound_raw_key, self._receipt_payload("WMS-REC-UNBOUND"))
        self.assertEqual(response.status_code, 403)

    def test_revoked_key_rejected(self):
        raw_key, key_record = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="To Be Revoked G", company=self.env.company, external_system=self.external_system,
        )
        key_record.action_revoke()
        response = self._post_receipt(raw_key, self._receipt_payload("WMS-REC-REVOKED"))
        self.assertEqual(response.status_code, 401)

    # -- 18/19. Status retrieval -------------------------------------------------

    def test_receipt_status_retrieval(self):
        create_resp = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-STATUS"))
        receipt_id = self._body(create_resp)["receipt_id"]
        response = self._get_receipt(self.bound_raw_key, "WMS-REC-STATUS")
        self.assertEqual(response.status_code, 200)
        body = self._body(response)
        self.assertEqual(body["receipt_id"], receipt_id)
        self.assertEqual(body["state"], "draft")
        self.assertIsNone(body["validated_at"])

    def test_dispatch_status_retrieval(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 5000,
        )
        create_resp = self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-STATUS"))
        dispatch_id = self._body(create_resp)["dispatch_id"]
        response = self._get_dispatch(self.bound_raw_key, "WMS-DISP-STATUS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._body(response)["dispatch_id"], dispatch_id)

    def test_status_retrieval_unknown_reference_404(self):
        response = self._get_receipt(self.bound_raw_key, "WMS-REC-NEVER-CREATED")
        self.assertEqual(response.status_code, 404)

    def test_status_retrieval_cross_system_404(self):
        self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-STATUS-CROSS"))
        response = self._get_receipt(self.second_system_raw_key, "WMS-REC-STATUS-CROSS")
        self.assertEqual(response.status_code, 404)

    # -- 20/21/22. Validation ------------------------------------------------------

    def test_receipt_validation(self):
        create_resp = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-VALIDATE"))
        body = self._body(create_resp)
        response = self._as_api_user(
            f"/cool_agristock/api/v1/receipts/{body['receipt_id']}/validate", method="POST", json={
                "external_reference": "WMS-REC-VALIDATE",
                "received_quantities": [{"product_id": self.product.id, "quantity": 5000}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "done")

        status = self._get_receipt(self.bound_raw_key, "WMS-REC-VALIDATE")
        self.assertIsNotNone(self._body(status)["validated_at"])

    def test_dispatch_validation(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 5000,
        )
        create_resp = self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-VALIDATE"))
        body = self._body(create_resp)
        response = self._as_api_user(
            f"/cool_agristock/api/v1/dispatches/{body['dispatch_id']}/validate", method="POST", json={
                "external_reference": "WMS-DISP-VALIDATE",
                "dispatched_quantities": [{"product_id": self.product.id, "quantity": 1500}],
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_repeated_validation_no_duplicate_stock_movement(self):
        create_resp = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-REPEAT-VALIDATE"))
        receipt_id = self._body(create_resp)["receipt_id"]
        payload = {
            "external_reference": "WMS-REC-REPEAT-VALIDATE",
            "received_quantities": [{"product_id": self.product.id, "quantity": 5000}],
        }
        first = self._as_api_user(f"/cool_agristock/api/v1/receipts/{receipt_id}/validate", method="POST", json=payload)
        self.assertEqual(first.status_code, 200)
        second = self._as_api_user(f"/cool_agristock/api/v1/receipts/{receipt_id}/validate", method="POST", json=payload)
        self.assertEqual(second.status_code, 409)

        move_count = self.env["stock.move"].search_count([("product_id", "=", self.product.id)])
        self.assertEqual(move_count, 1)

    # -- 23/24/25. Partial transactions / backorders ------------------------------

    def test_partial_receipt_rejected(self):
        create_resp = self._post_receipt(self.bound_raw_key, self._receipt_payload("WMS-REC-PARTIAL", quantity=5000))
        receipt_id = self._body(create_resp)["receipt_id"]
        response = self._as_api_user(
            f"/cool_agristock/api/v1/receipts/{receipt_id}/validate", method="POST", json={
                "external_reference": "WMS-REC-PARTIAL",
                "received_quantities": [{"product_id": self.product.id, "quantity": 2000}],
            },
        )
        self.assertEqual(response.status_code, 400)
        # No backorder silently created for the shortfall.
        self.assertEqual(
            self.env["stock.picking"].search_count([("backorder_id", "=", receipt_id)]), 0,
        )

    def test_partial_dispatch_rejected(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 5000,
        )
        create_resp = self._post_dispatch(self.bound_raw_key, self._dispatch_payload("WMS-DISP-PARTIAL", quantity=1500))
        dispatch_id = self._body(create_resp)["dispatch_id"]
        response = self._as_api_user(
            f"/cool_agristock/api/v1/dispatches/{dispatch_id}/validate", method="POST", json={
                "external_reference": "WMS-DISP-PARTIAL",
                "dispatched_quantities": [{"product_id": self.product.id, "quantity": 500}],
            },
        )
        self.assertEqual(response.status_code, 409)

    # -- 26/27. Lot-tracked receipt / dispatch ------------------------------------

    def test_lot_tracked_receipt(self):
        create_resp = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-LOT", product_external_id="PROD-LOT", lot_external_id="LOT-001",
        ))
        self.assertEqual(create_resp.status_code, 201)
        body = self._body(create_resp)
        response = self.url_open(
            f"/cool_agristock/api/v1/receipts/{body['receipt_id']}/validate", method="POST", json={
                "external_reference": "WMS-REC-LOT",
                "received_quantities": [{
                    "product_id": self.lot_tracked_product.id, "quantity": 5000,
                    "lot_external_id": "LOT-001",
                }],
            },
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 200)

    def test_lot_tracked_dispatch(self):
        self.env["stock.quant"]._update_available_quantity(
            self.lot_tracked_product, self.warehouse.lot_stock_id, 5000, lot_id=self.lot,
        )
        create_resp = self._post_dispatch(self.bound_raw_key, self._dispatch_payload(
            "WMS-DISP-LOT", product_external_id="PROD-LOT", lot_external_id="LOT-001",
        ))
        self.assertEqual(create_resp.status_code, 201)
        body = self._body(create_resp)
        response = self.url_open(
            f"/cool_agristock/api/v1/dispatches/{body['dispatch_id']}/validate", method="POST", json={
                "external_reference": "WMS-DISP-LOT",
                "dispatched_quantities": [{
                    "product_id": self.lot_tracked_product.id, "quantity": 1500,
                    "lot_external_id": "LOT-001",
                }],
            },
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 200)

    # -- 28/29. Serial-tracked receipt / dispatch ----------------------------------

    def test_serial_tracked_receipt(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-SERIAL", product_external_id="PROD-SERIAL", quantity=1,
            unit="unit", lot_external_id="SERIAL-001",
        ))
        self.assertEqual(response.status_code, 201)

    def test_serial_tracked_dispatch(self):
        self.env["stock.quant"]._update_available_quantity(
            self.serial_tracked_product, self.warehouse.lot_stock_id, 1, lot_id=self.serial_lot,
        )
        response = self._post_dispatch(self.bound_raw_key, self._dispatch_payload(
            "WMS-DISP-SERIAL", product_external_id="PROD-SERIAL", quantity=1,
            unit="unit", lot_external_id="SERIAL-001",
        ))
        self.assertEqual(response.status_code, 201)

    def test_tracked_product_without_lot_rejected(self):
        response = self._post_receipt(self.bound_raw_key, self._receipt_payload(
            "WMS-REC-NO-LOT", product_external_id="PROD-LOT",
        ))
        self.assertEqual(response.status_code, 422)

    # -- 30. Legacy API compatibility -----------------------------------------------

    def test_legacy_receipt_still_works(self):
        response = self._as_api_user("/cool_agristock/api/v1/receipts", method="POST", json={
            "external_reference": "COOL_AGRISTOCK-RCPT-PHASE-G",
            "warehouse_id": self.warehouse.id,
            "supplier_id": self.partner.id,
            "products": [{"product_id": self.product.id, "quantity": 10}],
        })
        self.assertEqual(response.status_code, 201)

    def test_legacy_dispatch_still_works(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 100,
        )
        response = self._as_api_user("/cool_agristock/api/v1/dispatches", method="POST", json={
            "external_reference": "COOL_AGRISTOCK-DISP-PHASE-G",
            "warehouse_id": self.warehouse.id,
            "customer_id": self.partner.id,
            "products": [{"product_id": self.product.id, "quantity": 10}],
        })
        self.assertEqual(response.status_code, 201)

    def test_both_schemas_at_once_rejected(self):
        payload = self._receipt_payload("WMS-REC-BOTH-SCHEMAS")
        payload["products"] = [{"product_id": self.product.id, "quantity": 10}]
        response = self._post_receipt(self.bound_raw_key, payload)
        self.assertEqual(response.status_code, 400)

    def test_existing_endpoints_unaffected(self):
        response = self.url_open(
            "/cool_agristock/api/v1/products", json={"external_id": "PHASE-G-CHECK", "name": "Still Works"},
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 201)
