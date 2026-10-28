from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockApiAuthentication(CoolAgristockApiCommon):
    """Requests must carry a valid Odoo API key, except for the health check."""

    def test_health_check_requires_no_authentication(self):
        response = self.url_open("/cool_agristock/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_products_without_authorization_header_is_unauthorized(self):
        response = self.url_open("/cool_agristock/api/v1/products")
        self.assertEqual(response.status_code, 401)

    def test_products_with_invalid_api_key_is_unauthorized(self):
        response = self.url_open(
            "/cool_agristock/api/v1/products",
            headers=self._auth_headers("not-a-real-api-key"),
        )
        self.assertEqual(response.status_code, 401)

    def test_create_receipt_without_authorization_header_is_unauthorized(self):
        response = self.url_open(
            "/cool_agristock/api/v1/receipts",
            json={},
            method="POST",
        )
        self.assertEqual(response.status_code, 401)

    def test_validate_receipt_without_authorization_header_is_unauthorized(self):
        response = self.url_open(
            "/cool_agristock/api/v1/receipts/1/validate",
            json={},
            method="POST",
        )
        self.assertEqual(response.status_code, 401)
