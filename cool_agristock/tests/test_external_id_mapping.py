import psycopg2

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockExternalIdMapping(CoolAgristockApiCommon):
    """cool_agristock.external.id.mapping: schema, constraints, and the
    resolve/create/update/remove mapping service."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_company = cls.env["res.company"].create({
            "name": "Cool Agristock Test Other Company",
        })

        internal_group = cls.env.ref("base.group_user")
        api_group = cls.env.ref("cool_agristock.group_cool_agristock_api_user")

        cls.other_api_user = cls.env["res.users"].create({
            "name": "Cool Agristock Other Company API User",
            "login": "cool_agristock_other_api_test_user",
            "group_ids": [(6, 0, [internal_group.id, api_group.id])],
            "company_ids": [(6, 0, [cls.other_company.id])],
            "company_id": cls.other_company.id,
        })

        cls.system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Main Warehouse WMS",
            "code": "primary_wms",
            "company_id": cls.env.company.id,
        })

        cls.other_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Other Company WMS",
            "code": "primary_wms",
            "company_id": cls.other_company.id,
        })

        cls.other_product = cls.env["product.product"].sudo().create({
            "name": "Other Company Test Product",
            "type": "consu",
            "is_storable": True,
            "company_id": cls.other_company.id,
        })

    def _mapping_model(self, user):
        return self.env["cool_agristock.external.id.mapping"].with_user(user)

    # -- Mapping creation ---------------------------------------------------

    def test_mapping_creation(self):
        Mapping = self._mapping_model(self.api_user)

        record, created = Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        self.assertTrue(created)
        self.assertEqual(record.res_id, self.product.id)
        self.assertEqual(record.external_id, "WMS-PRODUCT-001")

    def test_mapping_lookup(self):
        Mapping = self._mapping_model(self.api_user)

        Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        found = Mapping.resolve_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001",
        )
        self.assertTrue(found)
        self.assertEqual(found.res_id, self.product.id)

        not_found = Mapping.resolve_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-DOES-NOT-EXIST",
        )
        self.assertFalse(not_found)

    def test_mapping_updates(self):
        Mapping = self._mapping_model(self.api_user)

        Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        second_product = self.env["product.product"].sudo().create({
            "name": "Cool Agristock Second Test Product",
            "type": "consu",
            "is_storable": True,
        })

        updated = Mapping.update_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", second_product.id,
        )
        self.assertEqual(updated.res_id, second_product.id)

        with self.assertRaises(ValidationError):
            Mapping.update_mapping(
                self.env.company, self.system, "product.product",
                "WMS-PRODUCT-NEVER-CREATED", second_product.id,
            )

    def test_mapping_removal(self):
        Mapping = self._mapping_model(self.api_user)

        Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        removed_once = Mapping.remove_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001",
        )
        self.assertTrue(removed_once)

        # Idempotent: removing an already-gone mapping is not an error.
        removed_twice = Mapping.remove_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001",
        )
        self.assertFalse(removed_twice)

    # -- Conflict handling ----------------------------------------------------

    def test_duplicate_external_id_returns_existing_not_an_error(self):
        Mapping = self._mapping_model(self.api_user)

        first, created_first = Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )
        second, created_second = Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.id, second.id)

        count = self.env["cool_agristock.external.id.mapping"].sudo().search_count([
            ("company_id", "=", self.env.company.id),
            ("external_system_id", "=", self.system.id),
            ("res_model", "=", "product.product"),
            ("external_id", "=", "WMS-PRODUCT-001"),
        ])
        self.assertEqual(count, 1)

    def test_duplicate_odoo_record_mapping_rejected(self):
        Mapping = self._mapping_model(self.api_user)

        Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        # A *different* external_id pointing at the *same* Odoo record is a
        # genuine conflict (one record, two claimed identities) -- this must
        # propagate as an error, not be silently resolved like the
        # same-external_id case above.
        with self.assertRaises(Exception):
            Mapping.create_mapping(
                self.env.company, self.system, "product.product",
                "WMS-PRODUCT-002", self.product.id,
            )

    def test_different_external_systems_same_id_allowed(self):
        Mapping = self._mapping_model(self.admin_user)

        second_system = self.env["cool_agristock.external.system"].sudo().create({
            "name": "Secondary WMS",
            "code": "secondary_wms",
            "company_id": self.env.company.id,
        })
        second_product = self.env["product.product"].sudo().create({
            "name": "Cool Agristock Second System Product",
            "type": "consu",
            "is_storable": True,
        })

        _, created_a = Mapping.create_mapping(
            self.env.company, self.system, "product.product",
            "SHARED-ID", self.product.id,
        )
        _, created_b = Mapping.create_mapping(
            self.env.company, second_system, "product.product",
            "SHARED-ID", second_product.id,
        )

        self.assertTrue(created_a)
        self.assertTrue(created_b)

    def test_different_companies_same_id_allowed(self):
        Mapping_a = self._mapping_model(self.api_user)
        Mapping_b = self._mapping_model(self.other_api_user)

        _, created_a = Mapping_a.create_mapping(
            self.env.company, self.system, "product.product",
            "SHARED-ID", self.product.id,
        )
        _, created_b = Mapping_b.create_mapping(
            self.other_company, self.other_system, "product.product",
            "SHARED-ID", self.other_product.id,
        )

        self.assertTrue(created_a)
        self.assertTrue(created_b)

    # -- Validation -----------------------------------------------------------

    def test_invalid_target_record_rejected(self):
        nonexistent_id = self.product.id + 1000000

        with self.assertRaises(ValidationError):
            self.env["cool_agristock.external.id.mapping"].sudo().create({
                "company_id": self.env.company.id,
                "external_system_id": self.system.id,
                "res_model": "product.product",
                "external_id": "WMS-GHOST-PRODUCT",
                "res_id": nonexistent_id,
            })

    def test_unsupported_model_rejected(self):
        Mapping = self._mapping_model(self.api_user)

        with self.assertRaises(ValidationError):
            Mapping.create_mapping(
                self.env.company, self.system, "res.users",
                "WMS-USER-001", self.api_user.id,
            )

    def test_target_from_wrong_company_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["cool_agristock.external.id.mapping"].sudo().create({
                "company_id": self.env.company.id,
                "external_system_id": self.system.id,
                "res_model": "product.product",
                "external_id": "WMS-WRONG-COMPANY-PRODUCT",
                "res_id": self.other_product.id,
            })

    # -- Cross-company access -------------------------------------------------

    def test_cross_company_access_denied(self):
        Mapping = self._mapping_model(self.other_api_user)

        with self.assertRaises(AccessError):
            Mapping.create_mapping(
                self.env.company, self.system, "product.product",
                "WMS-PRODUCT-001", self.product.id,
            )

    def test_cross_company_resolve_denied(self):
        Mapping_a = self._mapping_model(self.api_user)
        Mapping_a.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        Mapping_b = self._mapping_model(self.other_api_user)
        with self.assertRaises(AccessError):
            Mapping_b.resolve_mapping(
                self.env.company, self.system, "product.product",
                "WMS-PRODUCT-001",
            )

    # -- Concurrency ------------------------------------------------------------

    def test_concurrent_mapping_creation_enforced_by_database(self):
        # Bypasses the service's own pre-check to prove the database
        # constraint -- not just the application-level check -- is what
        # actually prevents two concurrent requests from both succeeding.
        Model = self.env["cool_agristock.external.id.mapping"].sudo()

        Model.create({
            "company_id": self.env.company.id,
            "external_system_id": self.system.id,
            "res_model": "product.product",
            "external_id": "WMS-RACE-001",
            "res_id": self.product.id,
        })

        second_product = self.env["product.product"].sudo().create({
            "name": "Cool Agristock Race Test Product",
            "type": "consu",
            "is_storable": True,
        })

        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                Model.create({
                    "company_id": self.env.company.id,
                    "external_system_id": self.system.id,
                    "res_model": "product.product",
                    "external_id": "WMS-RACE-001",
                    "res_id": second_product.id,
                })

    # -- Administrator / API User access boundaries ----------------------------

    def test_administrator_has_read_only_mapping_access(self):
        Mapping_as_api_user = self._mapping_model(self.api_user)
        Mapping_as_api_user.create_mapping(
            self.env.company, self.system, "product.product",
            "WMS-PRODUCT-001", self.product.id,
        )

        # Administrators can read mappings directly (the admin-only
        # read-only view)...
        readable = self.env["cool_agristock.external.id.mapping"].with_user(
            self.admin_user
        ).search([("external_id", "=", "WMS-PRODUCT-001")])
        self.assertTrue(readable)

        # ...but cannot hand-edit them directly, by design.
        with self.assertRaises(AccessError):
            readable.with_user(self.admin_user).write({"res_id": self.product.id})

    def test_api_user_has_no_direct_mapping_access(self):
        with self.assertRaises(AccessError):
            self.env["cool_agristock.external.id.mapping"].with_user(
                self.api_user
            ).create({
                "company_id": self.env.company.id,
                "external_system_id": self.system.id,
                "res_model": "product.product",
                "external_id": "WMS-DIRECT-BYPASS",
                "res_id": self.product.id,
            })
