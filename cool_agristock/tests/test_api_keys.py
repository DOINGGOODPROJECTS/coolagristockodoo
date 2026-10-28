import datetime
import time

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockApiKeys(CoolAgristockApiCommon):
    """Self-service API key management: generation, expiration,
    revocation, multiple keys, and authorization boundaries."""

    def _generate(self, user, name="Test Integration", company=None,
                   expiration_date=None):
        return (
            self.env["cool_agristock.api.key"]
            .with_user(user)
            .generate_key(
                name=name,
                company=company or self.env.company,
                expiration_date=expiration_date,
            )
        )

    # -- Generation -----------------------------------------------------

    def test_generate_key_never_expires(self):
        raw_key, record = self._generate(self.admin_user, name="Main Warehouse")

        self.assertTrue(raw_key)
        self.assertEqual(record.state, "active")
        self.assertTrue(record.never_expires)
        self.assertFalse(record.expiration_date)
        self.assertEqual(record.company_id, self.env.company)
        self.assertTrue(record.integration_user_id)

    def test_generate_key_with_expiration(self):
        future = fields.Datetime.now() + datetime.timedelta(days=30)
        raw_key, record = self._generate(
            self.admin_user, name="Warehouse 2", expiration_date=future
        )

        self.assertTrue(raw_key)
        self.assertFalse(record.never_expires)
        self.assertEqual(record.state, "active")

    def test_multiple_keys_share_one_integration_identity(self):
        raw_key_1, record_1 = self._generate(self.admin_user, name="Integration A")
        raw_key_2, record_2 = self._generate(self.admin_user, name="Integration B")

        self.assertNotEqual(raw_key_1, raw_key_2)
        self.assertNotEqual(record_1.id, record_2.id)
        self.assertEqual(record_1.integration_user_id, record_2.integration_user_id)

    # -- Authorization ----------------------------------------------------

    def test_plain_user_cannot_generate_key(self):
        with self.assertRaises(AccessError):
            self._generate(self.plain_user)

    def test_api_user_without_admin_group_cannot_generate_key(self):
        with self.assertRaises(AccessError):
            self._generate(self.api_user)

    def test_admin_cannot_generate_key_for_unauthorized_company(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})

        with self.assertRaises(AccessError):
            self._generate(self.admin_user, company=other_company)

    def test_plain_user_cannot_revoke_key(self):
        _raw_key, record = self._generate(self.admin_user, name="Protected")

        with self.assertRaises(AccessError):
            record.with_user(self.plain_user).action_revoke()

    def test_user_from_other_company_cannot_revoke_key(self):
        _raw_key, record = self._generate(self.admin_user, name="Company A Key")

        other_company = self.env["res.company"].create({"name": "Other Co 2"})
        admin_group = self.env.ref(
            "cool_agristock.group_cool_agristock_administrator"
        )
        internal_group = self.env.ref("base.group_user")

        other_admin = self.env["res.users"].create({
            "name": "Other Company Admin",
            "login": "other_company_admin_test_user",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [other_company.id])],
            "company_id": other_company.id,
        })

        with self.assertRaises(AccessError):
            record.with_user(other_admin).action_revoke()

    # -- Revocation and expiration enforcement -----------------------------

    def test_revoke_immediately_invalidates_authentication(self):
        raw_key, record = self._generate(self.admin_user, name="Revoke Test")

        response = self.url_open(
            "/cool_agristock/api/v1/products", headers=self._auth_headers(raw_key)
        )
        self.assertEqual(response.status_code, 200)

        record.with_user(self.admin_user).action_revoke()
        self.assertEqual(record.state, "revoked")

        response = self.url_open(
            "/cool_agristock/api/v1/products", headers=self._auth_headers(raw_key)
        )
        self.assertEqual(response.status_code, 401)

    def test_revoke_is_idempotent(self):
        _raw_key, record = self._generate(self.admin_user, name="Double Revoke")

        record.with_user(self.admin_user).action_revoke()
        record.with_user(self.admin_user).action_revoke()

        self.assertEqual(record.state, "revoked")

    def test_expired_key_cannot_authenticate(self):
        past = fields.Datetime.now() - datetime.timedelta(days=1)
        raw_key, record = self._generate(
            self.admin_user, name="Already Expired", expiration_date=past
        )

        self.assertEqual(record.state, "expired")

        response = self.url_open(
            "/cool_agristock/api/v1/products", headers=self._auth_headers(raw_key)
        )
        self.assertEqual(response.status_code, 401)

    def test_status_updates_to_expired_purely_from_elapsed_time(self):
        """A key that was active at creation must show as expired once its
        expiration passes, even with no write to the record in between.
        Regression test: `state` must not be a stored compute field, or it
        would stay frozen at "active" forever.

        This only checks the ORM-level `state` display, not a REST call:
        the REST check compares against PostgreSQL's `now()`, which is
        fixed for the lifetime of a transaction, and this whole test method
        runs in one transaction (Odoo's test isolation), so a sleep() can
        never make it advance -- that part of the fix (a genuinely expired
        key getting rejected after elapsed time, no write in between) was
        verified live instead, across real separate HTTP requests, where
        PostgreSQL's `now()` does advance: generate -> wait past expiry ->
        confirm 401, matching test_expired_key_cannot_authenticate's
        same-transaction equivalent above.
        """
        # fields.Datetime.now() truncates to whole seconds and the compare
        # is "<=", so a margin of only ~1 second is a coin flip under load
        # (observed flaky in the full suite, never in isolation): a few
        # hundred ms of scheduling delay between computing `soon` and the
        # compute running is enough to land exactly on the same truncated
        # second. A multi-second margin removes that ambiguity entirely.
        soon = fields.Datetime.now() + datetime.timedelta(seconds=5)
        _raw_key, record = self._generate(
            self.admin_user, name="About To Expire", expiration_date=soon
        )
        self.assertEqual(record.state, "active")

        time.sleep(6)

        # A non-stored compute is still cached for the lifetime of an
        # environment; invalidating simulates the fresh env every real HTTP
        # request gets (Python's clock, unlike PostgreSQL's `now()`, does
        # advance within the test transaction).
        record.invalidate_recordset()

        self.assertEqual(record.state, "expired")

    def test_state_field_is_not_stored(self):
        """Deterministic guard against reintroducing store=True on `state`,
        which would freeze it at whatever it was computed as until some
        unrelated write happened to touch the record."""
        field = self.env["cool_agristock.api.key"]._fields["state"]
        self.assertFalse(
            field.store, "state must remain a non-stored compute field"
        )

    # -- Generate wizard --------------------------------------------------

    def test_wizard_requires_expiration_or_never_expires(self):
        wizard = (
            self.env["cool_agristock.api.key.generate.wizard"]
            .with_user(self.admin_user)
            .create({
                "name": "Incomplete",
                "company_id": self.env.company.id,
            })
        )

        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_wizard_rejects_past_expiration(self):
        past = fields.Datetime.now() - datetime.timedelta(days=1)
        wizard = (
            self.env["cool_agristock.api.key.generate.wizard"]
            .with_user(self.admin_user)
            .create({
                "name": "Past Date",
                "company_id": self.env.company.id,
                "expiration_date": past,
            })
        )

        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_wizard_generate_shows_key_once(self):
        wizard = (
            self.env["cool_agristock.api.key.generate.wizard"]
            .with_user(self.admin_user)
            .create({
                "name": "Wizard Success",
                "company_id": self.env.company.id,
                "never_expires": True,
            })
        )

        action = wizard.action_generate()

        self.assertEqual(action["res_model"], "res.users.apikeys.show")
        self.assertTrue(action["context"].get("default_key"))

    # -- Replacement keys ---------------------------------------------------

    def test_create_replacement_prefills_wizard_from_expired_key(self):
        past = fields.Datetime.now() - datetime.timedelta(days=1)
        _raw_key, record = self._generate(
            self.admin_user, name="Old Integration", expiration_date=past
        )
        self.assertEqual(record.state, "expired")

        action = record.with_user(self.admin_user).action_create_replacement()

        self.assertEqual(
            action["res_model"], "cool_agristock.api.key.generate.wizard"
        )
        self.assertEqual(action["context"]["default_name"], "Old Integration")
        self.assertEqual(
            action["context"]["default_company_id"], self.env.company.id
        )
        self.assertFalse(action["context"]["default_never_expires"])

    def test_create_replacement_prefills_never_expires(self):
        _raw_key, record = self._generate(self.admin_user, name="Permanent Key")

        action = record.with_user(self.admin_user).action_create_replacement()

        self.assertTrue(action["context"]["default_never_expires"])

    def test_create_replacement_round_trip_issues_independent_key(self):
        old_raw_key, old_record = self._generate(
            self.admin_user, name="Rotating Key"
        )
        old_record.with_user(self.admin_user).action_revoke()

        action = old_record.with_user(self.admin_user).action_create_replacement()

        wizard = (
            self.env["cool_agristock.api.key.generate.wizard"]
            .with_user(self.admin_user)
            .with_context(**action["context"])
            .create({})
        )
        new_action = wizard.action_generate()
        new_raw_key = new_action["context"]["default_key"]

        self.assertNotEqual(old_raw_key, new_raw_key)

        # The old key stays revoked; only the new one authenticates.
        response = self.url_open(
            "/cool_agristock/api/v1/products", headers=self._auth_headers(old_raw_key)
        )
        self.assertEqual(response.status_code, 401)

        response = self.url_open(
            "/cool_agristock/api/v1/products", headers=self._auth_headers(new_raw_key)
        )
        self.assertEqual(response.status_code, 200)

    def test_plain_user_cannot_create_replacement(self):
        _raw_key, record = self._generate(self.admin_user, name="Protected Key")
        record.with_user(self.admin_user).action_revoke()

        with self.assertRaises(AccessError):
            record.with_user(self.plain_user).action_create_replacement()
