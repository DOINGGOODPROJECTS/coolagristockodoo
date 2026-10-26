import json

from odoo.tests.common import tagged

from .common import AgriwareApiCommon


@tagged("-at_install", "post_install")
class TestAgriwareSupplierSync(AgriwareApiCommon):
    """POST/PATCH/GET /agriware/api/v1/suppliers: creation, updates,
    duplicate prevention, shared-partner protection, and the security
    matrix. Mirrors test_product_sync.py's structure."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        internal_group = cls.env.ref("base.group_user")
        admin_group = cls.env.ref("agriware_connector.group_agriware_administrator")

        cls.external_system = cls.env["agriware.external.system"].sudo().create({
            "name": "Primary WMS", "code": "primary_wms", "company_id": cls.env.company.id,
        })

        ApiKey = cls.env["agriware.api.key"].with_user(cls.admin_user)
        cls.bound_raw_key, cls.bound_key_record = ApiKey.generate_key(
            name="Bound WMS Key", company=cls.env.company, external_system=cls.external_system,
        )

        cls.unbound_only_company = cls.env["res.company"].create({
            "name": "Phase D Unbound-Only Company",
        })
        cls.unbound_only_admin_user = cls.env["res.users"].create({
            "name": "Phase D Unbound-Only Admin",
            "login": "agriware_phased_unbound_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.unbound_only_company.id])],
            "company_id": cls.unbound_only_company.id,
        })
        cls.unbound_raw_key, cls.unbound_key_record = cls.env["agriware.api.key"].with_user(
            cls.unbound_only_admin_user
        ).generate_key(name="Unbound Key", company=cls.unbound_only_company)

        cls.other_company = cls.env["res.company"].create({"name": "Phase D Other Company"})
        cls.other_admin_user = cls.env["res.users"].create({
            "name": "Phase D Other Company Admin",
            "login": "agriware_phased_other_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.other_company.id])],
            "company_id": cls.other_company.id,
        })
        cls.other_external_system = cls.env["agriware.external.system"].sudo().create({
            "name": "Other Co WMS", "code": "primary_wms", "company_id": cls.other_company.id,
        })
        cls.other_raw_key, cls.other_key_record = cls.env["agriware.api.key"].with_user(
            cls.other_admin_user
        ).generate_key(name="Other Co Key", company=cls.other_company, external_system=cls.other_external_system)

        cls.shared_partner = cls.env["res.partner"].sudo().create({
            "name": "Shared Across Companies", "company_id": False,
        })

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _post(self, key, data):
        return self.url_open("/agriware/api/v1/suppliers", json=data, headers=self._headers(key))

    def _patch(self, key, external_id, data):
        return self.url_open(
            f"/agriware/api/v1/suppliers/{external_id}",
            json=data, headers=self._headers(key), method="PATCH",
        )

    def _body(self, response):
        return json.loads(response.content)

    # -- Supplier creation ----------------------------------------------

    def test_create_supplier(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "SUP-001", "name": "Cooperative Agricole d'Anyama",
            "email": "contact@example.ci", "country_code": "CI",
        })
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        partner = self.env["res.partner"].sudo().browse(body["supplier_id"])
        self.assertEqual(partner.country_id.code, "CI")
        self.assertTrue(partner.agriware_is_supplier)
        # Phase D, Step 5: new suppliers are company-scoped, not shared.
        self.assertEqual(partner.company_id, self.env.company)

    def test_create_supplier_missing_name(self):
        response = self._post(self.bound_raw_key, {"external_id": "SUP-002"})
        self.assertEqual(response.status_code, 400)

    def test_create_supplier_unsupported_field_rejected(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "SUP-003", "name": "Has Credit Limit", "credit_limit": 10000,
        })
        self.assertEqual(response.status_code, 400)

    def test_create_supplier_invalid_country_code_rejected(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "SUP-004", "name": "Bad Country", "country_code": "ZZ",
        })
        self.assertEqual(response.status_code, 400)

    def test_get_suppliers(self):
        self._post(self.bound_raw_key, {"external_id": "SUP-GET", "name": "Listed Supplier"})
        unrelated = self.env["res.partner"].sudo().create({
            "name": "Ordinary Customer Contact",
            "company_id": self.env.company.id,
        })
        response = self.url_open(
            "/agriware/api/v1/suppliers", headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in self._body(response)["suppliers"]}
        self.assertNotIn(unrelated.id, ids)

    # -- Supplier updates -------------------------------------------------

    def test_update_supplier(self):
        self._post(self.bound_raw_key, {"external_id": "SUP-UPDATE", "name": "Original"})
        response = self._patch(self.bound_raw_key, "SUP-UPDATE", {"name": "Updated"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._body(response)["name"], "Updated")

    def test_update_unknown_external_id_returns_404(self):
        response = self._patch(self.bound_raw_key, "SUP-NEVER-CREATED", {"name": "Nope"})
        self.assertEqual(response.status_code, 404)

    def test_update_unsupported_field_rejected(self):
        self._post(self.bound_raw_key, {"external_id": "SUP-FIELD-LOCK", "name": "Locked"})
        response = self._patch(self.bound_raw_key, "SUP-FIELD-LOCK", {"property_payment_term_id": 1})
        self.assertEqual(response.status_code, 400)

    # -- Duplicate prevention -----------------------------------------------

    def test_duplicate_creation_rejected_no_duplicate_partner(self):
        first = self._post(self.bound_raw_key, {"external_id": "SUP-DUP", "name": "First"})
        self.assertEqual(first.status_code, 201)
        first_id = self._body(first)["supplier_id"]

        second = self._post(self.bound_raw_key, {"external_id": "SUP-DUP", "name": "Second"})
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self._body(second)["supplier_id"], first_id)

    # -- Shared partner protection --------------------------------------------

    def test_shared_partner_cannot_be_modified_even_if_mapped(self):
        # Simulates an administered adoption mapping onto a genuinely
        # shared (company_id=False) partner -- create_supplier() itself
        # never produces one, so this models the one way a shared
        # record could end up mapped (a manual administrative action),
        # and confirms the API still refuses to touch it.
        self.env["agriware.external.id.mapping"].sudo().create({
            "company_id": self.env.company.id,
            "external_system_id": self.external_system.id,
            "res_model": "res.partner",
            "external_id": "SUP-SHARED",
            "res_id": self.shared_partner.id,
        })
        response = self._patch(self.bound_raw_key, "SUP-SHARED", {"name": "Hijacked"})
        self.assertEqual(response.status_code, 409)

    # -- Cross-company / cross-system ----------------------------------------

    def test_cross_company_supplier_creation_isolated(self):
        response_a = self._post(self.bound_raw_key, {"external_id": "SUP-CROSS", "name": "Company A"})
        response_b = self._post(self.other_raw_key, {"external_id": "SUP-CROSS", "name": "Company B"})
        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 201)
        self.assertNotEqual(
            self._body(response_a)["supplier_id"], self._body(response_b)["supplier_id"],
        )

    def test_cross_company_update_rejected(self):
        self._post(self.bound_raw_key, {"external_id": "SUP-CROSS-UPDATE", "name": "Mine"})
        response = self._patch(self.other_raw_key, "SUP-CROSS-UPDATE", {"name": "Hijacked"})
        self.assertEqual(response.status_code, 404)

    # -- Security -------------------------------------------------------------

    def test_missing_api_key(self):
        response = self._post(None, {"external_id": "SUP-005", "name": "No Key"})
        self.assertEqual(response.status_code, 401)

    def test_unbound_key_rejected(self):
        response = self._post(self.unbound_raw_key, {"external_id": "SUP-006", "name": "Unbound"})
        self.assertEqual(response.status_code, 403)

    def test_unbound_key_still_works_for_get(self):
        response = self.url_open(
            "/agriware/api/v1/suppliers", headers=self._headers(self.unbound_raw_key),
        )
        self.assertEqual(response.status_code, 200)

    def test_inactive_external_system_rejected(self):
        self.external_system.sudo().active = False
        try:
            response = self._post(self.bound_raw_key, {"external_id": "SUP-007", "name": "Inactive"})
            self.assertEqual(response.status_code, 403)
        finally:
            self.external_system.sudo().active = True

    # -- Existing functionality compatibility --------------------------------

    def test_existing_endpoints_unaffected(self):
        response = self.url_open(
            "/agriware/api/v1/products", json={"external_id": "SUP-PHASE-CHECK", "name": "Still Works"},
            headers=self._headers(self.bound_raw_key),
        )
        self.assertEqual(response.status_code, 201)
