import json

from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockApiKeyIsolationSecurity(CoolAgristockApiCommon):
    """Mandatory pre-Phase-D security review: verifies the exact
    authorization isolation a bearer token's resolved external system
    must have from every *other* key sharing its company.

    This regression suite exists because the behavior it tests was
    empirically found broken: a key generated with no external_system
    binding (KEY_B below) was able to authenticate a product-write
    request and succeed, inheriting authorization from an unrelated key
    (KEY_A) that happened to share the same company. Reproduced via a
    real HTTP request against a disposable Odoo 19 database before any
    fix was written. See models/api_key.py's
    _create_dedicated_integration_user() for the fix (a key requesting
    a binding gets its own integration user, never shared with another
    key) and docs/EXTERNAL_ID_MAPPING.md's "API key binding" section
    for the full writeup.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ApiKey = cls.env["cool_agristock.api.key"].with_user(cls.admin_user)

        cls.system_a = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "System A", "code": "system_a", "company_id": cls.env.company.id,
        })
        cls.system_b = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "System B", "code": "system_b", "company_id": cls.env.company.id,
        })

        # Step 1-2: KEY_A, bound to SYSTEM_A.
        cls.key_a, cls.record_a = ApiKey.generate_key(
            name="KEY_A", company=cls.env.company, external_system=cls.system_a,
        )
        # Step 3: KEY_B, deliberately left unbound, same company as KEY_A.
        cls.key_b, cls.record_b = ApiKey.generate_key(
            name="KEY_B", company=cls.env.company,
        )

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"}

    def _post_product(self, key, external_id):
        return self.url_open(
            "/cool_agristock/api/v1/products",
            json={"external_id": external_id, "name": "Security Review Test"},
            headers=self._headers(key),
        )

    def _post_warehouse(self, key, external_id):
        return self.url_open(
            "/cool_agristock/api/v1/warehouses",
            json={"external_id": external_id, "name": "Security Review WH", "code": "SRW"},
            headers=self._headers(key),
        )

    def _body(self, response):
        return json.loads(response.content)

    # -- Steps 1-6: the core vulnerability, product endpoints -----------------

    def test_key_a_and_key_b_do_not_share_an_integration_user(self):
        # The root cause, verified directly: before the fix, these were
        # equal (both keys shared one per-company user).
        self.assertNotEqual(
            self.record_a.integration_user_id.id, self.record_b.integration_user_id.id,
        )

    def test_unbound_key_b_rejected_for_product_write(self):
        response = self._post_product(self.key_b, "SEC-REVIEW-PRODUCT-1")
        self.assertEqual(
            response.status_code, 403,
            "KEY_B has no external_system binding and must be rejected.",
        )

    def test_unbound_key_b_does_not_inherit_key_a_authorization(self):
        # Prove it's not merely "rejected for some other reason" --
        # confirm KEY_A (actually bound) succeeds under identical
        # conditions, so KEY_B's rejection is specifically about its own
        # lack of binding, not an unrelated failure.
        response_a = self._post_product(self.key_a, "SEC-REVIEW-PRODUCT-2")
        response_b = self._post_product(self.key_b, "SEC-REVIEW-PRODUCT-3")
        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 403)

    # -- Steps 7-9: binding KEY_B to a *different* system ----------------------

    def test_key_b_bound_to_system_b_cannot_touch_system_a_mappings(self):
        key_b2, record_b2 = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="KEY_B_BOUND", company=self.env.company, external_system=self.system_b,
        )

        # KEY_A creates a product under SYSTEM_A.
        response_a = self._post_product(self.key_a, "SEC-REVIEW-PRODUCT-A-OWNED")
        self.assertEqual(response_a.status_code, 201)

        # The newly-bound KEY_B cannot update it: from KEY_B's resolved
        # identity (SYSTEM_B), SYSTEM_A's mapping is invisible -- same
        # "404, not 403" behavior already proven for cross-company
        # access in test_product_sync.py, now proven cross-*system*
        # within the *same* company too.
        patch_response = self.url_open(
            "/cool_agristock/api/v1/products/SEC-REVIEW-PRODUCT-A-OWNED",
            json={"name": "Hijacked"}, headers=self._headers(key_b2), method="PATCH",
        )
        self.assertEqual(patch_response.status_code, 404)

    def test_authorized_system_derived_from_exact_token_presented(self):
        key_b2, record_b2 = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="KEY_B_BOUND_2", company=self.env.company, external_system=self.system_b,
        )

        resolve = self.env["cool_agristock.api.key"].sudo().resolve_authorized_external_system

        resolved_for_a = resolve(self.record_a.integration_user_id)
        resolved_for_b2 = resolve(record_b2.integration_user_id)

        self.assertEqual(resolved_for_a, self.system_a)
        self.assertEqual(resolved_for_b2, self.system_b)
        self.assertNotEqual(resolved_for_a, resolved_for_b2)

    # -- Step 10: repeat for warehouse endpoints -------------------------------

    def test_unbound_key_b_rejected_for_warehouse_write(self):
        response = self._post_warehouse(self.key_b, "SEC-REVIEW-WH-1")
        self.assertEqual(response.status_code, 403)

    def test_warehouse_unbound_key_b_does_not_inherit_key_a_authorization(self):
        response_a = self._post_warehouse(self.key_a, "SEC-REVIEW-WH-2")
        response_b = self._post_warehouse(self.key_b, "SEC-REVIEW-WH-3")
        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 403)

    def test_warehouse_key_b_bound_to_system_b_cannot_touch_system_a_mappings(self):
        key_b2, record_b2 = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="KEY_B_BOUND_WH", company=self.env.company, external_system=self.system_b,
        )

        response_a = self._post_warehouse(self.key_a, "SEC-REVIEW-WH-A-OWNED")
        self.assertEqual(response_a.status_code, 201)

        patch_response = self.url_open(
            "/cool_agristock/api/v1/warehouses/SEC-REVIEW-WH-A-OWNED",
            json={"name": "Hijacked"}, headers=self._headers(key_b2), method="PATCH",
        )
        self.assertEqual(patch_response.status_code, 404)

    # -- Confirms the existing shared-identity design is unaffected ------------

    def test_unbound_keys_still_share_one_integration_user(self):
        # The fix must not change behavior for keys that never request a
        # binding -- this is the exact scenario
        # test_api_keys.test_multiple_keys_share_one_integration_identity
        # already covers; re-asserted here as a direct regression check
        # tied to this security review.
        _, record_c = self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="KEY_C_UNBOUND", company=self.env.company,
        )
        self.assertEqual(record_c.integration_user_id, self.record_b.integration_user_id)
