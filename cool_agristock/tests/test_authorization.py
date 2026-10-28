from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockApiAuthorization(CoolAgristockApiCommon):
    """A valid API key is not enough: the owning user needs the Cool Agristock
    API User group (or a group that implies it)."""

    def test_plain_user_cannot_read_products(self):
        response = self._as_plain_user("/cool_agristock/api/v1/products")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "error")

    def test_plain_user_cannot_read_warehouses(self):
        response = self._as_plain_user("/cool_agristock/api/v1/warehouses")
        self.assertEqual(response.status_code, 403)

    def test_plain_user_cannot_read_inventory(self):
        response = self._as_plain_user("/cool_agristock/api/v1/inventory")
        self.assertEqual(response.status_code, 403)

    def test_plain_user_cannot_create_receipt(self):
        response = self._as_plain_user(
            "/cool_agristock/api/v1/receipts",
            json={
                "external_reference": "COOL_AGRISTOCK-RCPT-AUTHZ-1",
                "warehouse_id": self.warehouse.id,
                "supplier_id": self.partner.id,
                "products": [{"product_id": self.product.id, "quantity": 10}],
            },
            method="POST",
        )
        self.assertEqual(response.status_code, 403)

    def test_plain_user_cannot_create_dispatch(self):
        response = self._as_plain_user(
            "/cool_agristock/api/v1/dispatches",
            json={
                "external_reference": "COOL_AGRISTOCK-DISP-AUTHZ-1",
                "warehouse_id": self.warehouse.id,
                "customer_id": self.partner.id,
                "products": [{"product_id": self.product.id, "quantity": 10}],
            },
            method="POST",
        )
        self.assertEqual(response.status_code, 403)

    def test_api_user_can_read_products(self):
        response = self._as_api_user("/cool_agristock/api/v1/products")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
