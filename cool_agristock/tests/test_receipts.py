from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockReceipts(CoolAgristockApiCommon):

    def _create_payload(self, reference="COOL_AGRISTOCK-RCPT-1", quantity=100):
        return {
            "external_reference": reference,
            "warehouse_id": self.warehouse.id,
            "supplier_id": self.partner.id,
            "products": [{"product_id": self.product.id, "quantity": quantity}],
        }

    def _create(self, payload):
        return self._as_api_user(
            "/cool_agristock/api/v1/receipts", json=payload, method="POST"
        )

    def _validate(self, receipt_id, payload):
        return self._as_api_user(
            f"/cool_agristock/api/v1/receipts/{receipt_id}/validate",
            json=payload,
            method="POST",
        )

    def test_create_receipt_success(self):
        response = self._create(self._create_payload())
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["state"], "draft")

        picking = self.env["stock.picking"].browse(body["receipt_id"])
        self.assertEqual(picking.origin, "COOL_AGRISTOCK-RCPT-1")
        self.assertEqual(picking.partner_id, self.partner)

    def test_create_receipt_invalid_json_is_rejected(self):
        response = self._as_api_user(
            "/cool_agristock/api/v1/receipts",
            data=b"not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_receipt_missing_external_reference_is_rejected(self):
        payload = self._create_payload()
        payload["external_reference"] = ""
        response = self._create(payload)
        self.assertEqual(response.status_code, 400)

    def test_create_receipt_invalid_warehouse_is_not_found(self):
        payload = self._create_payload()
        payload["warehouse_id"] = 999999
        response = self._create(payload)
        self.assertEqual(response.status_code, 404)

    def test_create_receipt_invalid_supplier_is_not_found(self):
        payload = self._create_payload()
        payload["supplier_id"] = 999999
        response = self._create(payload)
        self.assertEqual(response.status_code, 404)

    def test_create_receipt_non_storable_product_is_rejected(self):
        payload = self._create_payload()
        payload["products"] = [
            {"product_id": self.service_product.id, "quantity": 5}
        ]
        response = self._create(payload)
        self.assertEqual(response.status_code, 400)

    def test_create_receipt_too_many_product_lines_is_rejected(self):
        payload = self._create_payload()
        payload["products"] = [
            {"product_id": self.product.id, "quantity": 1} for _ in range(101)
        ]
        response = self._create(payload)
        self.assertEqual(response.status_code, 400)

    def test_duplicate_external_reference_is_conflict(self):
        payload = self._create_payload(reference="COOL_AGRISTOCK-RCPT-DUP")

        first = self._create(payload)
        self.assertEqual(first.status_code, 201)
        first_receipt_id = first.json()["receipt_id"]

        second = self._create(payload)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["receipt_id"], first_receipt_id)

    def test_validate_receipt_success(self):
        created = self._create(self._create_payload(
            reference="COOL_AGRISTOCK-RCPT-VALIDATE", quantity=50
        ))
        self.assertEqual(created.status_code, 201)
        receipt_id = created.json()["receipt_id"]

        response = self._validate(receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-VALIDATE",
            "received_quantities": [
                {"product_id": self.product.id, "quantity": 50}
            ],
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["state"], "done")

    def test_validate_receipt_quantity_mismatch_is_conflict(self):
        created = self._create(self._create_payload(
            reference="COOL_AGRISTOCK-RCPT-MISMATCH", quantity=50
        ))
        receipt_id = created.json()["receipt_id"]

        response = self._validate(receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-MISMATCH",
            "received_quantities": [
                {"product_id": self.product.id, "quantity": 10}
            ],
        })
        self.assertEqual(response.status_code, 400)

    def test_validate_receipt_wrong_reference_is_forbidden(self):
        """Only references using the COOL_AGRISTOCK-RCPT- prefix are validatable
        through this API, even if they otherwise match an existing draft
        incoming picking."""
        picking_type = self.warehouse.in_type_id
        manual_picking = self.env["stock.picking"].create({
            "partner_id": self.partner.id,
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
            "origin": "MANUAL-NOT-COOL_AGRISTOCK",
        })

        response = self._validate(manual_picking.id, {
            "external_reference": "MANUAL-NOT-COOL_AGRISTOCK",
            "received_quantities": [
                {"product_id": self.product.id, "quantity": 1}
            ],
        })
        self.assertEqual(response.status_code, 403)

    def test_validate_receipt_already_done_is_conflict(self):
        created = self._create(self._create_payload(
            reference="COOL_AGRISTOCK-RCPT-TWICE", quantity=20
        ))
        receipt_id = created.json()["receipt_id"]

        payload = {
            "external_reference": "COOL_AGRISTOCK-RCPT-TWICE",
            "received_quantities": [
                {"product_id": self.product.id, "quantity": 20}
            ],
        }
        first = self._validate(receipt_id, payload)
        self.assertEqual(first.status_code, 200)

        second = self._validate(receipt_id, payload)
        self.assertEqual(second.status_code, 409)

    def test_validate_receipt_lot_tracked_product_is_rejected(self):
        created = self._create({
            "external_reference": "COOL_AGRISTOCK-RCPT-LOT",
            "warehouse_id": self.warehouse.id,
            "supplier_id": self.partner.id,
            "products": [
                {"product_id": self.lot_tracked_product.id, "quantity": 10}
            ],
        })
        self.assertEqual(created.status_code, 201)
        receipt_id = created.json()["receipt_id"]

        response = self._validate(receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-LOT",
            "received_quantities": [
                {"product_id": self.lot_tracked_product.id, "quantity": 10}
            ],
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["message"],
            "Lot or serial tracking is not supported yet",
        )

    def test_validate_receipt_serial_tracked_product_is_rejected(self):
        created = self._create({
            "external_reference": "COOL_AGRISTOCK-RCPT-SERIAL",
            "warehouse_id": self.warehouse.id,
            "supplier_id": self.partner.id,
            "products": [
                {"product_id": self.serial_tracked_product.id, "quantity": 1}
            ],
        })
        self.assertEqual(created.status_code, 201)
        receipt_id = created.json()["receipt_id"]

        response = self._validate(receipt_id, {
            "external_reference": "COOL_AGRISTOCK-RCPT-SERIAL",
            "received_quantities": [
                {"product_id": self.serial_tracked_product.id, "quantity": 1}
            ],
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["message"],
            "Lot or serial tracking is not supported yet",
        )
