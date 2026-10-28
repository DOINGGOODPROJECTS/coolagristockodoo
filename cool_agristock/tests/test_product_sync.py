import json

from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockProductSync(CoolAgristockApiCommon):
    """POST/PATCH /cool_agristock/api/v1/products: API-key-to-external-system
    binding, product creation, updates, duplicate prevention, and the
    full security matrix."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Primary WMS",
            "code": "primary_wms",
            "company_id": cls.env.company.id,
        })

        ApiKey = cls.env["cool_agristock.api.key"].with_user(cls.admin_user)

        # Generated through the real cool_agristock.api.key.generate_key() flow
        # (not common.py's raw apikeys fixture, which has no
        # cool_agristock.api.key record at all and so can never resolve an
        # external system) -- bound, authorized for product writes.
        cls.bound_raw_key, cls.bound_key_record = ApiKey.generate_key(
            name="Bound WMS Key", company=cls.env.company, external_system=cls.external_system,
        )

        # A second key bound to the *same* external system -- multiple
        # keys sharing one authorization outcome is expected, not an
        # error (they share the same integration user already).
        cls.bound_raw_key_2, cls.bound_key_record_2 = ApiKey.generate_key(
            name="Second Bound WMS Key", company=cls.env.company, external_system=cls.external_system,
        )

        internal_group = cls.env.ref("base.group_user")
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")

        # A key generated for a company with NO bound key at all.
        #
        # Important: all of a company's cool_agristock.api.key records share
        # ONE integration user (_get_or_create_integration_user), and
        # Odoo's Bearer auth only ever tells a controller which USER
        # authenticated -- never which specific key row. So "unbound"
        # is, in practice, a property of a company's whole shared
        # integration identity, not of one individual named key: if this
        # key were generated for cls.env.company (which already has a
        # key bound to cls.external_system), it would inherit that
        # binding too. A dedicated company with no bound key anywhere
        # is the only way to test genuine non-binding. See
        # docs/PRODUCT_SYNCHRONIZATION.md's Known limitations.
        cls.unbound_only_company = cls.env["res.company"].create({
            "name": "Phase B Unbound-Only Company",
        })
        cls.unbound_only_admin_user = cls.env["res.users"].create({
            "name": "Phase B Unbound-Only Admin",
            "login": "cool_agristock_phaseb_unbound_admin",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.unbound_only_company.id])],
            "company_id": cls.unbound_only_company.id,
        })
        cls.unbound_raw_key, cls.unbound_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.unbound_only_admin_user
        ).generate_key(
            name="Unbound Key", company=cls.unbound_only_company,
        )

        cls.other_company = cls.env["res.company"].create({"name": "Phase B Other Company"})
        cls.other_admin_user = cls.env["res.users"].create({
            "name": "Phase B Other Company Admin",
            "login": "cool_agristock_phaseb_other_admin",
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
        ).generate_key(
            name="Other Co Key", company=cls.other_company, external_system=cls.other_external_system,
        )

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"} if key else {}

    def _post(self, key, data):
        return self.url_open(
            "/cool_agristock/api/v1/products", json=data, headers=self._headers(key),
        )

    def _patch(self, key, external_id, data):
        return self.url_open(
            f"/cool_agristock/api/v1/products/{external_id}",
            json=data, headers=self._headers(key), method="PATCH",
        )

    def _body(self, response):
        return json.loads(response.content)

    # -- API key binding --------------------------------------------------

    def test_bound_key_authorized_for_product_creation(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-001", "name": "Cassava", "unit": "kg",
        })
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["external_id"], "AGRI-001")

    def test_unbound_key_rejected_for_product_creation(self):
        response = self._post(self.unbound_raw_key, {
            "external_id": "AGRI-002", "name": "Maize",
        })
        self.assertEqual(response.status_code, 403)

    def test_unbound_key_still_works_for_existing_endpoints(self):
        # Backward compatibility: a key with no external_system binding
        # must be entirely unaffected for every pre-existing endpoint.
        response = self.url_open(
            "/cool_agristock/api/v1/products", headers=self._headers(self.unbound_raw_key),
        )
        self.assertEqual(response.status_code, 200)

    def test_two_keys_bound_to_same_system_both_authorized(self):
        response_1 = self._post(self.bound_raw_key, {
            "external_id": "AGRI-SHARED-1", "name": "Product A",
        })
        response_2 = self._post(self.bound_raw_key_2, {
            "external_id": "AGRI-SHARED-2", "name": "Product B",
        })
        self.assertEqual(response_1.status_code, 201)
        self.assertEqual(response_2.status_code, 201)

    def test_inactive_external_system_rejected(self):
        self.external_system.sudo().active = False
        try:
            response = self._post(self.bound_raw_key, {
                "external_id": "AGRI-INACTIVE", "name": "Should Fail",
            })
            self.assertEqual(response.status_code, 403)
        finally:
            self.external_system.sudo().active = True

    # -- Authentication -----------------------------------------------------

    def test_missing_api_key(self):
        response = self._post(None, {"external_id": "AGRI-003", "name": "No Key"})
        self.assertEqual(response.status_code, 401)

    def test_invalid_api_key(self):
        response = self._post("not-a-real-key", {"external_id": "AGRI-004", "name": "Bad Key"})
        self.assertEqual(response.status_code, 401)

    def test_revoked_api_key_rejected(self):
        raw_key, record = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="To Be Revoked", company=self.env.company, external_system=self.external_system,
        )
        record.with_user(self.admin_user).action_revoke()
        response = self._post(raw_key, {"external_id": "AGRI-005", "name": "Revoked"})
        self.assertEqual(response.status_code, 401)

    def test_expired_api_key_rejected(self):
        import datetime
        from odoo import fields
        past = fields.Datetime.now() - datetime.timedelta(days=1)
        raw_key, record = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="Expired Key", company=self.env.company,
            expiration_date=fields.Datetime.now() + datetime.timedelta(seconds=1),
            external_system=self.external_system,
        )
        # Force the underlying apikeys row into the past directly --
        # generate_key()/_check_expiration_date() won't accept a past
        # date, so this simulates time having passed since a valid key
        # was issued, rather than testing an input validation error.
        self.env.cr.execute(
            "UPDATE res_users_apikeys SET expiration_date = %s WHERE id = %s",
            (past, record.apikey_id.id),
        )
        response = self._post(raw_key, {"external_id": "AGRI-006", "name": "Expired"})
        self.assertEqual(response.status_code, 401)

    # -- Product creation ---------------------------------------------------

    def test_create_product_default_unit(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-DEFAULT-UNIT", "name": "No Unit Specified",
        })
        self.assertEqual(response.status_code, 201)
        body = self._body(response)
        product = self.env["product.product"].sudo().browse(body["product_id"])
        self.assertEqual(product.uom_id, self.env.ref("uom.product_uom_unit"))

    def test_create_product_unsupported_unit_rejected(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-BAD-UNIT", "name": "Bad Unit", "unit": "bag",
        })
        self.assertEqual(response.status_code, 400)

    def test_create_product_unsupported_field_rejected(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-BAD-FIELD", "name": "Has Price",
            "list_price": 100,
        })
        self.assertEqual(response.status_code, 400)

    def test_create_product_missing_name_rejected(self):
        response = self._post(self.bound_raw_key, {"external_id": "AGRI-NO-NAME"})
        self.assertEqual(response.status_code, 400)

    def test_created_product_has_no_stock_quantity(self):
        response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-NO-STOCK", "name": "No Stock Yet",
        })
        body = self._body(response)
        quants = self.env["stock.quant"].sudo().search([
            ("product_id", "=", body["product_id"]),
        ])
        self.assertFalse(quants)

    # -- Product updates ------------------------------------------------------

    def test_update_product(self):
        create_response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-UPDATE-ME", "name": "Original Name",
        })
        self.assertEqual(create_response.status_code, 201)

        update_response = self._patch(
            self.bound_raw_key, "AGRI-UPDATE-ME", {"name": "Updated Name"},
        )
        self.assertEqual(update_response.status_code, 200)
        body = self._body(update_response)
        self.assertEqual(body["name"], "Updated Name")

    def test_update_unknown_external_id_returns_404(self):
        response = self._patch(
            self.bound_raw_key, "AGRI-NEVER-CREATED", {"name": "Doesn't Matter"},
        )
        self.assertEqual(response.status_code, 404)

    def test_update_does_not_create_product(self):
        self._patch(self.bound_raw_key, "AGRI-PATCH-NO-CREATE", {"name": "Should Not Exist"})
        mapping = self.env["cool_agristock.external.id.mapping"].sudo().search([
            ("external_id", "=", "AGRI-PATCH-NO-CREATE"),
        ])
        self.assertFalse(mapping)

    def test_update_unsupported_field_rejected(self):
        self._post(self.bound_raw_key, {"external_id": "AGRI-UOM-LOCK", "name": "Locked Unit"})
        response = self._patch(
            self.bound_raw_key, "AGRI-UOM-LOCK", {"unit": "kg"},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_preserves_odoo_specific_fields(self):
        create_response = self._post(self.bound_raw_key, {
            "external_id": "AGRI-PRESERVE", "name": "Preserve Me",
        })
        product_id = self._body(create_response)["product_id"]
        self.env["product.product"].sudo().browse(product_id).list_price = 42.0

        self._patch(self.bound_raw_key, "AGRI-PRESERVE", {"name": "Preserve Me Updated"})

        product = self.env["product.product"].sudo().browse(product_id)
        self.assertEqual(product.list_price, 42.0)

    # -- Duplicate prevention -------------------------------------------------

    def test_duplicate_creation_rejected_no_duplicate_product(self):
        first = self._post(self.bound_raw_key, {
            "external_id": "AGRI-DUPLICATE", "name": "First Attempt",
        })
        self.assertEqual(first.status_code, 201)
        first_product_id = self._body(first).get("product_id")

        second = self._post(self.bound_raw_key, {
            "external_id": "AGRI-DUPLICATE", "name": "Second Attempt",
        })
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self._body(second).get("product_id"), first_product_id)

        count = self.env["product.product"].sudo().search_count([
            ("name", "in", ["First Attempt", "Second Attempt"]),
        ])
        self.assertEqual(count, 1)

    # -- Cross-company / cross-system access ----------------------------------

    def test_cross_company_key_cannot_update_other_companys_product(self):
        self._post(self.bound_raw_key, {"external_id": "AGRI-CROSS-CO", "name": "Mine"})

        response = self._patch(
            self.other_raw_key, "AGRI-CROSS-CO", {"name": "Hijacked"},
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_system_same_external_id_independent(self):
        response_a = self._post(self.bound_raw_key, {
            "external_id": "AGRI-SAME-ID", "name": "Company A Product",
        })
        response_b = self._post(self.other_raw_key, {
            "external_id": "AGRI-SAME-ID", "name": "Company B Product",
        })
        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 201)
        self.assertNotEqual(
            self._body(response_a)["product_id"], self._body(response_b)["product_id"],
        )
