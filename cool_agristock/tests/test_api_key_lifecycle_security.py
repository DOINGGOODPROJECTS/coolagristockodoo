from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockApiKeyLifecycleSecurity(CoolAgristockApiCommon):
    """Phase D's Step 2 review: does any key lifecycle event (rotation,
    revocation, reassignment, external-system deactivation) let a
    dedicated integration user retain or regain unintended
    authorization? Companion to test_api_key_isolation_security.py,
    which covers the original same-request-time vulnerability; this
    file covers what happens *over time* as keys are rotated."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Lifecycle Test System", "code": "lifecycle_sys",
            "company_id": cls.env.company.id,
        })

    def _generate(self, name, external_system=None):
        return self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name=name, company=self.env.company, external_system=external_system,
        )

    # -- Rotation ---------------------------------------------------------

    def test_key_rotation_replacement_gets_a_fresh_dedicated_user(self):
        raw_original, original = self._generate("Original", self.system)
        original.with_user(self.admin_user).action_revoke()

        raw_replacement, replacement = self._generate("Replacement", self.system)

        self.assertNotEqual(
            original.integration_user_id.id, replacement.integration_user_id.id,
            "A rotated key must never reuse the revoked key's integration user.",
        )

    def test_revoked_key_no_longer_authorizes_after_rotation(self):
        raw_original, original = self._generate("Original2", self.system)
        original.with_user(self.admin_user).action_revoke()
        self._generate("Replacement2", self.system)

        resolve = self.env["cool_agristock.api.key"].sudo().resolve_authorized_external_system
        self.assertFalse(resolve(original.integration_user_id))

    def test_replacement_resolves_correctly_to_the_same_system(self):
        raw_original, original = self._generate("Original3", self.system)
        original.with_user(self.admin_user).action_revoke()
        raw_replacement, replacement = self._generate("Replacement3", self.system)

        resolve = self.env["cool_agristock.api.key"].sudo().resolve_authorized_external_system
        self.assertEqual(resolve(replacement.integration_user_id), self.system)

    # -- Revocation / expiration do not leave residual authorization ---------

    def test_revoked_bound_key_state_is_revoked_and_unauthorized(self):
        raw_key, record = self._generate("ToRevoke", self.system)
        record.with_user(self.admin_user).action_revoke()

        self.assertEqual(record.state, "revoked")
        resolve = self.env["cool_agristock.api.key"].sudo().resolve_authorized_external_system
        self.assertFalse(resolve(record.integration_user_id))

    # -- Reassignment / direct-write safeguard (defense in depth) ------------

    def test_cannot_make_two_bound_keys_share_an_integration_user(self):
        # Simulates a hypothetical future bug or a hand-edited/legacy
        # record that tries to reuse an existing dedicated user for a
        # second bound key -- exactly the shape of the original
        # vulnerability, attempted via direct ORM write rather than
        # generate_key(). The model-level constraint must reject it
        # regardless of how the write was made.
        raw_key_a, record_a = self._generate("KeyA", self.system)
        raw_key_b, record_b = self._generate("KeyB", self.system)

        with self.assertRaises(ValidationError):
            record_b.sudo().write({
                "integration_user_id": record_a.integration_user_id.id,
            })

    def test_unbound_keys_sharing_a_user_remain_unaffected_by_the_safeguard(self):
        # The safeguard must only fire for *bound* keys -- unbound keys
        # sharing the per-company user is the long-standing, intended,
        # unchanged design (test_multiple_keys_share_one_integration_identity).
        raw_key_1, record_1 = self._generate("Unbound1")
        raw_key_2, record_2 = self._generate("Unbound2")

        self.assertEqual(record_1.integration_user_id, record_2.integration_user_id)

        # Re-saving one of them (a no-op write, just to re-trigger the
        # constraint) must not raise, since neither is bound.
        record_2.sudo().write({"name": "Unbound2 Renamed"})

    # -- External system deactivation ----------------------------------------

    def test_deactivating_external_system_revokes_authorization_live(self):
        raw_key, record = self._generate("LiveDeactivateTest", self.system)
        resolve = self.env["cool_agristock.api.key"].sudo().resolve_authorized_external_system

        self.assertEqual(resolve(record.integration_user_id), self.system)

        self.system.sudo().active = False
        self.assertFalse(resolve(record.integration_user_id))

        self.system.sudo().active = True
        self.assertEqual(resolve(record.integration_user_id), self.system)

    # -- Legacy-key compatibility ---------------------------------------------

    def test_legacy_style_unbound_key_still_authenticates_existing_endpoints(self):
        # "Legacy" here means a key generated the same way every key was
        # generated before external_system_id existed at all: no binding
        # argument passed. Confirms that code path -- and the shared
        # per-company user it has always used -- is completely untouched
        # by any of this phase's or the prior security fix's changes.
        raw_key, record = self._generate("LegacyStyleKey")

        response = self.url_open(
            "/cool_agristock/api/v1/products", headers={"Authorization": f"Bearer {raw_key}"},
        )
        self.assertEqual(response.status_code, 200)
