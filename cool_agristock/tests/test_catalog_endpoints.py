from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockCatalogEndpoints(CoolAgristockApiCommon):
    """Read-only product, warehouse, and inventory endpoints."""

    def test_products_returns_created_product(self):
        response = self._as_api_user("/cool_agristock/api/v1/products")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        ids = [p["id"] for p in body["products"]]
        self.assertIn(self.product.id, ids)

    def test_warehouses_returns_test_warehouse(self):
        response = self._as_api_user("/cool_agristock/api/v1/warehouses")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        ids = [w["id"] for w in body["warehouses"]]
        self.assertIn(self.warehouse.id, ids)

    def test_inventory_reflects_on_hand_quantity(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 25
        )

        response = self._as_api_user("/cool_agristock/api/v1/inventory")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")

        line = next(
            (i for i in body["inventory"] if i["product_id"] == self.product.id),
            None,
        )
        self.assertIsNotNone(line)
        self.assertEqual(line["quantity"], 25)
