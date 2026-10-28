from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockDispatches(CoolAgristockApiCommon):

    def _create_payload(self, reference="COOL_AGRISTOCK-DISP-1", quantity=10):
        return {
            "external_reference": reference,
            "warehouse_id": self.warehouse.id,
            "customer_id": self.partner.id,
            "products": [{"product_id": self.product.id, "quantity": quantity}],
        }

    def _create(self, payload):
        return self._as_api_user(
            "/cool_agristock/api/v1/dispatches", json=payload, method="POST"
        )

    def _validate(self, dispatch_id, payload):
        return self._as_api_user(
            f"/cool_agristock/api/v1/dispatches/{dispatch_id}/validate",
            json=payload,
            method="POST",
        )

    def _stock_product(self, quantity):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, quantity
        )

    def test_create_dispatch_success(self):
        response = self._create(self._create_payload())
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["state"], "draft")

    def test_create_dispatch_invalid_quantity_is_rejected(self):
        payload = self._create_payload()
        payload["products"] = [{"product_id": self.product.id, "quantity": -5}]
        response = self._create(payload)
        self.assertEqual(response.status_code, 400)

    def test_create_dispatch_invalid_customer_is_not_found(self):
        payload = self._create_payload()
        payload["customer_id"] = 999999
        response = self._create(payload)
        self.assertEqual(response.status_code, 404)

    def test_create_dispatch_duplicate_product_lines_is_rejected(self):
        payload = self._create_payload()
        payload["products"] = [
            {"product_id": self.product.id, "quantity": 5},
            {"product_id": self.product.id, "quantity": 5},
        ]
        response = self._create(payload)
        self.assertEqual(response.status_code, 400)

    def test_duplicate_external_reference_is_conflict(self):
        payload = self._create_payload(reference="COOL_AGRISTOCK-DISP-DUP")

        first = self._create(payload)
        self.assertEqual(first.status_code, 201)
        first_dispatch_id = first.json()["dispatch_id"]

        second = self._create(payload)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["dispatch_id"], first_dispatch_id)

    def test_validate_dispatch_success(self):
        self._stock_product(100)

        created = self._create(self._create_payload(
            reference="COOL_AGRISTOCK-DISP-VALIDATE", quantity=15
        ))
        self.assertEqual(created.status_code, 201)
        dispatch_id = created.json()["dispatch_id"]

        response = self._validate(dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-VALIDATE",
            "dispatched_quantities": [
                {"product_id": self.product.id, "quantity": 15}
            ],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"], "done")

    def test_validate_dispatch_insufficient_stock_is_conflict(self):
        self._stock_product(1)

        created = self._create(self._create_payload(
            reference="COOL_AGRISTOCK-DISP-NOSTOCK", quantity=15
        ))
        dispatch_id = created.json()["dispatch_id"]

        response = self._validate(dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-NOSTOCK",
            "dispatched_quantities": [
                {"product_id": self.product.id, "quantity": 15}
            ],
        })
        self.assertEqual(response.status_code, 409)

    def test_validate_dispatch_unscoped_reference_is_forbidden(self):
        """Only references using the COOL_AGRISTOCK-DISP- prefix are validatable
        through this API, even if they otherwise match an existing draft
        outgoing picking."""
        picking_type = self.warehouse.out_type_id
        manual_picking = self.env["stock.picking"].create({
            "partner_id": self.partner.id,
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
            "origin": "MANUAL-NOT-COOL_AGRISTOCK",
        })

        response = self._validate(manual_picking.id, {
            "external_reference": "MANUAL-NOT-COOL_AGRISTOCK",
            "dispatched_quantities": [
                {"product_id": self.product.id, "quantity": 5}
            ],
        })
        self.assertEqual(response.status_code, 403)

    def test_validate_dispatch_lot_tracked_product_is_rejected(self):
        created = self._create({
            "external_reference": "COOL_AGRISTOCK-DISP-LOT",
            "warehouse_id": self.warehouse.id,
            "customer_id": self.partner.id,
            "products": [
                {"product_id": self.lot_tracked_product.id, "quantity": 10}
            ],
        })
        self.assertEqual(created.status_code, 201)
        dispatch_id = created.json()["dispatch_id"]

        response = self._validate(dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-LOT",
            "dispatched_quantities": [
                {"product_id": self.lot_tracked_product.id, "quantity": 10}
            ],
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["message"],
            "Lot or serial tracking is not supported yet",
        )

    def test_validate_dispatch_serial_tracked_product_is_rejected(self):
        created = self._create({
            "external_reference": "COOL_AGRISTOCK-DISP-SERIAL",
            "warehouse_id": self.warehouse.id,
            "customer_id": self.partner.id,
            "products": [
                {"product_id": self.serial_tracked_product.id, "quantity": 1}
            ],
        })
        self.assertEqual(created.status_code, 201)
        dispatch_id = created.json()["dispatch_id"]

        response = self._validate(dispatch_id, {
            "external_reference": "COOL_AGRISTOCK-DISP-SERIAL",
            "dispatched_quantities": [
                {"product_id": self.serial_tracked_product.id, "quantity": 1}
            ],
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["message"],
            "Lot or serial tracking is not supported yet",
        )
