import json

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged

from .common import CoolAgristockApiCommon


@tagged("-at_install", "post_install")
class TestCoolAgristockUomMapping(CoolAgristockApiCommon):
    """cool_agristock.uom.mapping: schema, constraints, admin-only access, and
    its integration into product synchronization."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.external_system = cls.env["cool_agristock.external.system"].sudo().create({
            "name": "Primary WMS", "code": "primary_wms", "company_id": cls.env.company.id,
        })

        cls.bound_raw_key, cls.bound_key_record = cls.env["cool_agristock.api.key"].with_user(
            cls.admin_user
        ).generate_key(name="Bound Key", company=cls.env.company, external_system=cls.external_system)

        cls.other_company = cls.env["res.company"].create({"name": "UOM Test Other Company"})

    def _headers(self, key):
        return {"Authorization": f"Bearer {key}"}

    def _post_product(self, data):
        return self.url_open(
            "/cool_agristock/api/v1/products", json=data, headers=self._headers(self.bound_raw_key),
        )

    def _body(self, response):
        return json.loads(response.content)

    # -- Model-level: creation, constraints, access --------------------------

    def test_create_uom_mapping(self):
        mapping = self.env["cool_agristock.uom.mapping"].with_user(self.admin_user).create({
            "company_id": self.env.company.id,
            "external_system_id": self.external_system.id,
            "external_unit_code": "bag_50kg",
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
            "description": "This WMS's 50kg bag, fertilizer products only.",
        })
        self.assertTrue(mapping.active)

    def test_duplicate_uom_mapping_rejected(self):
        Model = self.env["cool_agristock.uom.mapping"].with_user(self.admin_user)
        Model.create({
            "company_id": self.env.company.id,
            "external_system_id": self.external_system.id,
            "external_unit_code": "bag_50kg",
            "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                Model.create({
                    "company_id": self.env.company.id,
                    "external_system_id": self.external_system.id,
                    "external_unit_code": "bag_50kg",
                    "uom_id": self.env.ref("uom.product_uom_ton").id,
                })

    def test_same_code_different_company_allowed(self):
        other_system = self.env["cool_agristock.external.system"].sudo().create({
            "name": "Other WMS", "code": "primary_wms", "company_id": self.other_company.id,
        })
        Model = self.env["cool_agristock.uom.mapping"].sudo()
        m1 = Model.create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "external_unit_code": "bag_50kg", "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        m2 = Model.create({
            "company_id": self.other_company.id, "external_system_id": other_system.id,
            "external_unit_code": "bag_50kg", "uom_id": self.env.ref("uom.product_uom_ton").id,
        })
        self.assertNotEqual(m1.id, m2.id)

    def test_api_user_has_no_direct_access(self):
        with self.assertRaises(AccessError):
            self.env["cool_agristock.uom.mapping"].with_user(self.api_user).create({
                "company_id": self.env.company.id,
                "external_system_id": self.external_system.id,
                "external_unit_code": "bag_50kg",
                "uom_id": self.env.ref("uom.product_uom_kgm").id,
            })

    def test_plain_user_has_no_access(self):
        with self.assertRaises(AccessError):
            self.env["cool_agristock.uom.mapping"].with_user(self.plain_user).create({
                "company_id": self.env.company.id,
                "external_system_id": self.external_system.id,
                "external_unit_code": "bag_50kg",
                "uom_id": self.env.ref("uom.product_uom_kgm").id,
            })

    # -- resolve_unit() service ------------------------------------------------

    def test_resolve_unit_found(self):
        self.env["cool_agristock.uom.mapping"].sudo().create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "external_unit_code": "bag_50kg", "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        resolved = self.env["cool_agristock.uom.mapping"].resolve_unit(
            self.env.company, self.external_system, "bag_50kg",
        )
        self.assertEqual(resolved, self.env.ref("uom.product_uom_kgm"))

    def test_resolve_unit_not_found_returns_empty(self):
        resolved = self.env["cool_agristock.uom.mapping"].resolve_unit(
            self.env.company, self.external_system, "totally_unconfigured_code",
        )
        self.assertFalse(resolved)

    def test_resolve_unit_ignores_inactive_mapping(self):
        mapping = self.env["cool_agristock.uom.mapping"].sudo().create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "external_unit_code": "bag_50kg", "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        mapping.sudo().active = False
        resolved = self.env["cool_agristock.uom.mapping"].resolve_unit(
            self.env.company, self.external_system, "bag_50kg",
        )
        self.assertFalse(resolved)

    # -- Integration with product synchronization ------------------------------

    def test_product_sync_resolves_admin_configured_unit(self):
        self.env["cool_agristock.uom.mapping"].sudo().create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "external_unit_code": "bag_50kg", "uom_id": self.env.ref("uom.product_uom_kgm").id,
        })
        response = self._post_product({
            "external_id": "UOM-TEST-001", "name": "Bagged Cassava", "unit": "bag_50kg",
        })
        self.assertEqual(response.status_code, 201)
        product = self.env["product.product"].sudo().browse(self._body(response)["product_id"])
        self.assertEqual(product.uom_id, self.env.ref("uom.product_uom_kgm"))

    def test_product_sync_backward_compatible_without_any_mapping_configured(self):
        # No cool_agristock.uom.mapping row exists at all for this company --
        # the Phase B hardcoded set must still work exactly as before.
        response = self._post_product({
            "external_id": "UOM-TEST-002", "name": "Plain Kg Product", "unit": "kg",
        })
        self.assertEqual(response.status_code, 201)
        product = self.env["product.product"].sudo().browse(self._body(response)["product_id"])
        self.assertEqual(product.uom_id, self.env.ref("uom.product_uom_kgm"))

    def test_product_sync_rejects_unconfigured_and_unsupported_unit(self):
        # "carton" is neither hardcoded nor configured -- must be
        # rejected, never silently guessed or defaulted.
        response = self._post_product({
            "external_id": "UOM-TEST-003", "name": "Carton Product", "unit": "carton",
        })
        self.assertEqual(response.status_code, 400)

    def test_configured_mapping_takes_precedence_over_hardcoded_set(self):
        # Configure "kg" (already a hardcoded code) to resolve to a
        # *different* UOM than the hardcoded default, proving the
        # admin-configured mapping is actually consulted first, not
        # just used as a fallback for codes the hardcoded set doesn't
        # already cover.
        self.env["cool_agristock.uom.mapping"].sudo().create({
            "company_id": self.env.company.id, "external_system_id": self.external_system.id,
            "external_unit_code": "kg", "uom_id": self.env.ref("uom.product_uom_ton").id,
        })
        response = self._post_product({
            "external_id": "UOM-TEST-004", "name": "Overridden Kg Product", "unit": "kg",
        })
        self.assertEqual(response.status_code, 201)
        product = self.env["product.product"].sudo().browse(self._body(response)["product_id"])
        self.assertEqual(product.uom_id, self.env.ref("uom.product_uom_ton"))
