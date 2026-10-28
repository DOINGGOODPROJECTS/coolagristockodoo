import json

from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockLocationSync(CoolAgristockApiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Location Test WMS",
            "code": "location_test",
            "company_id": cls.env.company.id,
        })
        cls.raw_key, cls.key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.admin_user,
        ).generate_key(
            name="Location Test Key",
            company=cls.env.company,
            external_system=cls.external_system,
        )
        cls.env["cool_agristock.external.id.mapping"].sudo().create({
            "company_id": cls.env.company.id,
            "external_system_id": cls.external_system.id,
            "res_model": "stock.warehouse",
            "external_id": "LOC-WH",
            "res_id": cls.warehouse.id,
        })

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _post(self, key, payload):
        return self.url_open(
            "/cool_agristock/api/v1/locations", json=payload, headers=self._headers(key),
        )

    def _body(self, response):
        return json.loads(response.content)

    def test_get_locations_returns_internal_locations(self):
        response = self.url_open(
            "/cool_agristock/api/v1/locations", headers=self._headers(self.raw_key),
        )
        self.assertEqual(response.status_code, 200)
        body = self._body(response)
        self.assertIn("locations", body)
        self.assertTrue(any(
            item["id"] == self.warehouse.lot_stock_id.id
            for item in body["locations"]
        ))

    def test_create_and_update_location(self):
        created = self._post(self.raw_key, {
            "external_id": "BIN-A1",
            "warehouse_external_id": "LOC-WH",
            "name": "Aisle A Bin 1",
            "barcode": "BIN-A1",
        })
        self.assertEqual(created.status_code, 201, created.content)
        body = self._body(created)
        location = self.env["stock.location"].sudo().browse(body["location_id"])
        self.assertEqual(location.usage, "internal")
        self.assertEqual(location.company_id, self.env.company)
        self.assertEqual(location.location_id, self.warehouse.lot_stock_id)
        self.assertEqual(
            self.env["cool_agristock.external.id.mapping"].sudo().search_count([
                ("external_system_id", "=", self.external_system.id),
                ("res_model", "=", "stock.location"),
                ("external_id", "=", "BIN-A1"),
            ]),
            1,
        )
        updated = self.url_open(
            "/cool_agristock/api/v1/locations/BIN-A1",
            json={"name": "Aisle A Bin 1 Updated"},
            headers=self._headers(self.raw_key),
            method="PATCH",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(self._body(updated)["name"], "Aisle A Bin 1 Updated")

    def test_create_nested_location_from_mapped_parent(self):
        parent_response = self._post(self.raw_key, {
            "external_id": "AISLE-A",
            "warehouse_external_id": "LOC-WH",
            "name": "Aisle A",
        })
        self.assertEqual(parent_response.status_code, 201, parent_response.content)
        child_response = self._post(self.raw_key, {
            "external_id": "BIN-A2",
            "warehouse_external_id": "LOC-WH",
            "parent_external_id": "AISLE-A",
            "name": "Bin A2",
        })
        self.assertEqual(child_response.status_code, 201, child_response.content)
        child = self.env["stock.location"].sudo().browse(
            self._body(child_response)["location_id"],
        )
        self.assertEqual(child.location_id.name, "Aisle A")

    def test_unbound_key_cannot_create_location(self):
        response = self._post(None, {
            "external_id": "NO-AUTH",
            "warehouse_external_id": "LOC-WH",
            "name": "Unauthorized",
        })
        self.assertEqual(response.status_code, 401)

    def test_rejects_unsupported_location_fields(self):
        response = self._post(self.raw_key, {
            "external_id": "BAD-FIELD",
            "warehouse_external_id": "LOC-WH",
            "name": "Unsafe",
            "usage": "supplier",
        })
        self.assertEqual(response.status_code, 400)
