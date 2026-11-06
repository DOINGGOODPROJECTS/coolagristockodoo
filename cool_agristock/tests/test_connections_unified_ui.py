from datetime import timedelta

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestConnectionWizard(CoolAgristockApiCommon):
    """The guided 'Add Connection' wizard: creates an external system and
    its first API key together, in one step."""

    def test_wizard_creates_connection_and_key(self):
        wizard = self.env["cool_agristock.connection.wizard"].with_user(
            self.admin_user
        ).create({
            "name": "Main Agricultural Warehouse",
            "wms_name": "Cool Agristock WMS",
            "expiration_preset": "never",
        })

        result = wizard.action_generate()
        self.assertEqual(result["res_model"], "res.users.apikeys.show")
        self.assertTrue(result["context"]["default_key"])

        connection = self.env["cool_agristock.external.system"].sudo().search([
            ("name", "=", "Main Agricultural Warehouse"),
        ])
        self.assertTrue(connection)
        self.assertEqual(connection.wms_name, "Cool Agristock WMS")
        self.assertEqual(connection.active_api_key_count, 1)
        self.assertEqual(connection.connection_status, "awaiting_first_connection")

    def test_wizard_requires_admin(self):
        with self.assertRaises(AccessError):
            self.env["cool_agristock.connection.wizard"].with_user(
                self.plain_user
            ).create({
                "name": "Unauthorized Attempt",
                "wms_name": "Some WMS",
                "expiration_preset": "never",
            })

    def test_wizard_custom_expiration_must_be_future(self):
        wizard = self.env["cool_agristock.connection.wizard"].with_user(
            self.admin_user
        ).create({
            "name": "Bad Expiration",
            "wms_name": "Some WMS",
            "expiration_preset": "custom",
            "expiration_date": "2000-01-01 00:00:00",
        })
        with self.assertRaises(UserError):
            wizard.action_generate()

    def test_wizard_unique_code_on_name_collision(self):
        Wizard = self.env["cool_agristock.connection.wizard"].with_user(self.admin_user)

        Wizard.create({
            "name": "Duplicate Name",
            "wms_name": "WMS A",
            "expiration_preset": "never",
        }).action_generate()

        Wizard.create({
            "name": "Duplicate Name",
            "wms_name": "WMS B",
            "expiration_preset": "never",
        }).action_generate()

        connections = self.env["cool_agristock.external.system"].sudo().search([
            ("name", "=", "Duplicate Name"),
        ])
        self.assertEqual(len(connections), 2)
        self.assertNotEqual(connections[0].code, connections[1].code)


@tagged("-at_install", "post_install")
class TestConnectionStatus(TransactionCase):
    """connection_status must only ever reflect real, derivable signals --
    never a fabricated 'Connected'."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")
        cls.admin_user = cls.env["res.users"].create({
            "name": "Status Test Admin",
            "login": "cool_agristock_status_test_admin",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, admin_group.id])],
            "company_ids": [(6, 0, [cls.env.company.id])],
            "company_id": cls.env.company.id,
        })

    def test_no_active_key(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "No Key Connection",
            "code": "no_key_connection",
        })
        self.assertEqual(connection.connection_status, "no_active_key")

    def test_awaiting_first_connection(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Awaiting Connection",
            "code": "awaiting_connection",
        })
        self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="key", company=self.env.company, external_system=connection,
        )
        connection.invalidate_recordset()
        self.assertEqual(connection.connection_status, "awaiting_first_connection")

    def test_active_once_activity_recorded(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Active Connection",
            "code": "active_connection",
        })
        self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="key", company=self.env.company, external_system=connection,
        )
        self.env["cool_agristock.api.activity.log"].create({
            "company_id": self.env.company.id,
            "external_system_id": connection.id,
            "endpoint": "GET /cool_agristock/api/v1/health",
            "http_status": 200,
        })
        connection.invalidate_recordset()
        self.assertEqual(connection.connection_status, "active")

    def test_inactive_regardless_of_keys_or_activity(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Disabled Connection",
            "code": "disabled_connection",
        })
        self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="key", company=self.env.company, external_system=connection,
        )
        connection.with_user(self.admin_user).action_deactivate()
        self.assertEqual(connection.connection_status, "inactive")

    def test_revoking_only_key_drops_to_no_active_key(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Revoked Key Connection",
            "code": "revoked_key_connection",
        })
        _raw, key = self.env["cool_agristock.api.key"].with_user(
            self.admin_user
        ).generate_key(name="key", company=self.env.company, external_system=connection)

        key.with_user(self.admin_user).action_revoke()
        connection.invalidate_recordset()
        self.assertEqual(connection.connection_status, "no_active_key")


@tagged("-at_install", "post_install")
class TestConnectionTestAction(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        admin_group = cls.env.ref("cool_agristock.group_cool_agristock_administrator")
        cls.admin_user = cls.env["res.users"].create({
            "name": "Test Action Admin",
            "login": "cool_agristock_test_action_admin",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, admin_group.id])],
            "company_ids": [(6, 0, [cls.env.company.id])],
            "company_id": cls.env.company.id,
        })

    def test_requires_active_key(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "No Key Test", "code": "no_key_test",
        })
        with self.assertRaises(UserError):
            connection.with_user(self.admin_user).action_test_connection()

    def test_requires_connection_active(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Inactive Test", "code": "inactive_test",
        })
        self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="key", company=self.env.company, external_system=connection,
        )
        connection.with_user(self.admin_user).action_deactivate()
        with self.assertRaises(UserError):
            connection.with_user(self.admin_user).action_test_connection()

    def test_succeeds_with_active_key(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Ready Test", "code": "ready_test",
        })
        self.env["cool_agristock.api.key"].with_user(self.admin_user).generate_key(
            name="key", company=self.env.company, external_system=connection,
        )
        result = connection.with_user(self.admin_user).action_test_connection()
        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("cool_agristock/api/v1/health", result["params"]["message"])
        # Must never claim the external WMS is actually connected from
        # configuration alone.
        self.assertNotIn("is connected", result["params"]["message"].lower())


@tagged("-at_install", "post_install")
class TestApiActivityLog(CoolAgristockApiCommon):
    """Confirms activity is actually recorded.

    Deliberately exercised through POST /products (not a readonly=True
    GET route): Odoo's own test harness refuses to open a second
    read/write cursor from inside a readonly one (TestCursor's own
    safety rail against leaking writes outside a test's rollback
    sandbox), so a readonly route's activity-log write is a no-op
    *within automated tests specifically* -- confirmed separately, by
    hand, against a real running server (not under the test harness),
    where it works correctly; see test_readonly_route_still_responds_ok
    below for what *is* reliably testable about that path: logging
    failure must never break the actual response.
    """

    def test_write_route_success_is_logged(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Logging Success Connection", "code": "logging_success_connection",
        })
        raw_key, _key = self.env["cool_agristock.api.key"].with_user(
            self.admin_user
        ).generate_key(name="key", company=self.env.company, external_system=connection)

        response = self.url_open(
            "/cool_agristock/api/v1/products",
            json={"external_id": "ACTIVITY-LOG-1", "name": "Logged Product"},
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        self.assertEqual(response.status_code, 201)

        entry = self.env["cool_agristock.api.activity.log"].sudo().search([
            ("external_system_id", "=", connection.id),
        ], order="id desc", limit=1)
        self.assertTrue(entry, "Expected an activity log entry for this connection")
        self.assertEqual(entry.http_status, 201)
        self.assertTrue(entry.success)
        self.assertFalse(entry.error_category)
        self.assertEqual(entry.endpoint, "POST /cool_agristock/api/v1/products")

    def test_write_route_validation_failure_is_logged_with_category(self):
        connection = self.env["cool_agristock.external.system"].create({
            "name": "Logging Validation Connection", "code": "logging_validation_connection",
        })
        raw_key, _key = self.env["cool_agristock.api.key"].with_user(
            self.admin_user
        ).generate_key(name="key", company=self.env.company, external_system=connection)

        response = self.url_open(
            "/cool_agristock/api/v1/products",
            json={"external_id": "ACTIVITY-LOG-NO-NAME"},
            headers={"Authorization": f"Bearer {raw_key}"},
            method="POST",
        )
        self.assertEqual(response.status_code, 400)

        entry = self.env["cool_agristock.api.activity.log"].sudo().search([
            ("endpoint", "=", "POST /cool_agristock/api/v1/products"),
            ("http_status", "=", 400),
        ], order="id desc", limit=1)
        self.assertTrue(entry)
        self.assertEqual(entry.error_category, "validation_error")
        self.assertFalse(entry.success)

    def test_readonly_route_still_responds_ok(self):
        """The important guarantee for readonly routes: a logging hiccup
        (real production-side logging works; only Odoo's own test harness
        blocks it) must never break the actual API response."""
        response = self._as_api_user("/cool_agristock/api/v1/products")
        self.assertEqual(response.status_code, 200)


@tagged("-at_install", "post_install")
class TestApiActivityLogRetention(TransactionCase):

    def test_old_entries_are_purged_recent_entries_are_kept(self):
        Log = self.env["cool_agristock.api.activity.log"]

        old_entry = Log.create({
            "company_id": self.env.company.id,
            "endpoint": "GET /cool_agristock/api/v1/health",
            "http_status": 200,
        })
        recent_entry = Log.create({
            "company_id": self.env.company.id,
            "endpoint": "GET /cool_agristock/api/v1/health",
            "http_status": 200,
        })

        backdated = old_entry.create_date - timedelta(days=200)
        self.env.cr.execute(
            "UPDATE cool_agristock_api_activity_log SET create_date = %s WHERE id = %s",
            (backdated, old_entry.id),
        )
        old_entry.invalidate_recordset()

        Log._gc_activity_log()

        self.assertFalse(old_entry.exists())
        self.assertTrue(recent_entry.exists())
