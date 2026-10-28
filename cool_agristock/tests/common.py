from odoo.tests.common import HttpCase


class CoolAgristockApiCommon(HttpCase):
    """Shared fixtures for Cool Agristock API tests.

    Runs as ``HttpCase`` (not ``TransactionCase``) because the endpoints are
    real HTTP routes using ``auth="bearer"``, which can only be exercised
    through an actual HTTP request with an ``Authorization`` header. Each
    test still runs in its own rolled-back savepoint, so nothing persists to
    the database once the test suite finishes.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )

        cls.product = cls.env["product.product"].create({
            "name": "Cool Agristock Test Product",
            "type": "consu",
            "is_storable": True,
        })

        cls.service_product = cls.env["product.product"].create({
            "name": "Cool Agristock Service (not stock-tracked)",
            "type": "service",
        })

        cls.lot_tracked_product = cls.env["product.product"].create({
            "name": "Cool Agristock Lot Tracked Product",
            "type": "consu",
            "is_storable": True,
            "tracking": "lot",
        })

        cls.serial_tracked_product = cls.env["product.product"].create({
            "name": "Cool Agristock Serial Tracked Product",
            "type": "consu",
            "is_storable": True,
            "tracking": "serial",
        })

        cls.partner = cls.env["res.partner"].create({
            "name": "Cool Agristock Test Partner",
        })

        api_group = cls.env.ref("cool_agristock.group_cool_agristock_api_user")
        admin_group = cls.env.ref(
            "cool_agristock.group_cool_agristock_administrator"
        )
        internal_group = cls.env.ref("base.group_user")

        cls.api_user = cls.env["res.users"].create({
            "name": "Cool Agristock API Test User",
            "login": "cool_agristock_api_test_user",
            "group_ids": [(6, 0, [internal_group.id, api_group.id])],
        })

        cls.plain_user = cls.env["res.users"].create({
            "name": "Cool Agristock Plain Test User",
            "login": "cool_agristock_plain_test_user",
            "group_ids": [(6, 0, [internal_group.id])],
        })

        cls.admin_user = cls.env["res.users"].create({
            "name": "Cool Agristock Administrator Test User",
            "login": "cool_agristock_admin_test_user",
            "group_ids": [(6, 0, [internal_group.id, admin_group.id])],
            "company_ids": [(6, 0, [cls.env.company.id])],
            "company_id": cls.env.company.id,
        })

        api_keys = cls.env["res.users.apikeys"]

        cls.api_key = (
            api_keys.with_user(cls.api_user)
            .sudo()
            ._generate(scope=None, name="Test Key", expiration_date=None)
        )

        cls.plain_key = (
            api_keys.with_user(cls.plain_user)
            .sudo()
            ._generate(scope=None, name="Test Key", expiration_date=None)
        )

    def _auth_headers(self, key):
        return {"Authorization": f"Bearer {key}"}

    def _as_api_user(self, path, **kwargs):
        headers = {**self._auth_headers(self.api_key), **kwargs.pop("headers", {})}
        return self.url_open(path, headers=headers, **kwargs)

    def _as_plain_user(self, path, **kwargs):
        headers = {**self._auth_headers(self.plain_key), **kwargs.pop("headers", {})}
        return self.url_open(path, headers=headers, **kwargs)
