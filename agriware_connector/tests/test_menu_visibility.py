from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestAgriwareMenuVisibility(TransactionCase):
    """Regression guard: the `groups` shortcut on <menuitem> only ever adds
    to group_ids on module upgrade, it never removes a previously-declared
    group. A menu that changes which group restricts it (or drops the
    restriction entirely) needs an explicit (6, 0, ...) override, or an
    existing, already-upgraded database keeps the old restriction forever
    alongside the new one -- silently hiding the menu from everyone who
    only has the new group. This was caught live on a long-lived dev
    database that still carried a stale base.group_system restriction from
    this module's very first release.
    """

    def test_root_menu_has_no_stale_group_restriction(self):
        menu = self.env.ref("agriware_connector.menu_agriware_root")
        self.assertFalse(
            menu.group_ids,
            "The root menu must stay unrestricted so visibility is "
            "controlled entirely by each child menu's own groups.",
        )

    def test_wms_connections_menu_is_restricted_to_technical_features_only(self):
        menu = self.env.ref("agriware_connector.menu_agriware_connections")
        self.assertEqual(
            menu.group_ids,
            self.env.ref("base.group_no_one"),
            "WMS Connections must be hidden from normal users (including "
            "plain System Administrators) and reachable only with "
            "Technical Features enabled.",
        )

    def test_api_management_menu_is_restricted_to_agriware_administrator(self):
        menu = self.env.ref("agriware_connector.menu_agriware_api_management")
        self.assertEqual(
            menu.group_ids,
            self.env.ref("agriware_connector.group_agriware_administrator"),
        )

    def test_suppliers_menu_is_available_from_inventory_products(self):
        menu = self.env.ref("agriware_connector.menu_agriware_suppliers")
        action = self.env.ref("agriware_connector.action_agriware_suppliers")
        self.assertEqual(
            menu.parent_id,
            self.env.ref("agriware_connector.menu_agriware_suppliers_root"),
        )
        self.assertEqual(action.res_model, "res.partner")
        self.assertIn(
            self.env.ref("stock.group_stock_user"),
            menu.group_ids,
        )

    def test_dashboard_menu_opens_live_overview(self):
        menu = self.env.ref("agriware_connector.menu_agriware_dashboard")
        action = self.env.ref("agriware_connector.action_agriware_dashboard")
        self.assertEqual(menu.action, action)
        self.assertEqual(action.res_model, "agriware.dashboard")

    def test_storage_location_menu_uses_native_odoo_action(self):
        menu = self.env.ref("agriware_connector.menu_agriware_locations")
        self.assertEqual(menu.action, self.env.ref("stock.action_location_form"))

    def test_ordinary_inventory_user_can_open_dashboard_and_operational_menus(self):
        user = self.env["res.users"].create({
            "name": "Navigation Operator", "login": "navigation_operator",
            "group_ids": [(6, 0, [self.env.ref("stock.group_stock_user").id])],
            "company_ids": [(6, 0, self.env.company.ids)],
            "company_id": self.env.company.id,
        })
        self.assertFalse(user.has_group("base.group_system"))
        dashboard = self.env["agriware.dashboard"].with_user(user).create({})
        self.assertGreaterEqual(dashboard.active_system_count, 0)
        for method in ("products", "inventory", "warehouses", "receipts",
                       "dispatches", "lots", "suppliers", "inventory_imports"):
            action = getattr(dashboard, "action_open_" + method)()
            model = self.env[action["res_model"]].with_user(user)
            self.assertTrue(model.has_access("read"), action["name"])
            model.get_views([(False, "list"), (False, "form")])
        visible = self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()
        for name in ("dashboard", "products", "inventory", "stock_adjustments",
                     "lots", "warehouses", "locations", "receipts", "dispatches",
                     "stock_movements", "suppliers"):
            self.assertIn(self.env.ref("agriware_connector.menu_agriware_" + name).id, visible)
        for name in ("api_management", "external_systems", "sync_history"):
            self.assertNotIn(self.env.ref("agriware_connector.menu_agriware_" + name).id, visible)

    def test_dashboard_metrics_are_scoped_to_selected_companies(self):
        company = self.env["res.company"].create({"name": "Other Dashboard Company"})
        self.env["agriware.external.system"].create({
            "name": "Other WMS", "code": "dashboard_other", "company_id": company.id,
        })
        dashboard = self.env["agriware.dashboard"].with_context(
            allowed_company_ids=[company.id],
        ).create({})
        self.assertEqual(dashboard.active_system_count, 1)
        self.assertEqual(dashboard.receipt_count, 0)
        self.assertEqual(dashboard.dispatch_count, 0)

    def test_all_visible_connector_actions_load_for_connector_administrator(self):
        user = self.env["res.users"].create({
            "name": "Navigation Administrator", "login": "navigation_administrator",
            "group_ids": [(6, 0, [self.env.ref(
                "agriware_connector.group_agriware_administrator").id])],
        })
        menu_model = self.env["ir.ui.menu"].with_user(user)
        visible = menu_model._visible_menu_ids()
        root = self.env.ref("agriware_connector.menu_agriware_root")
        for menu in menu_model.search([("id", "child_of", root.id)]):
            if menu.id not in visible or not menu.action:
                continue
            # The web action loader reads action metadata with sudo; business
            # records and view loading must still use the ordinary user.
            action = menu.action.sudo()
            if action._name == "ir.actions.server":
                values = action.with_user(user).run()
                model_name = values["res_model"]
                views = values.get("views", [(False, "list")])
            else:
                model_name = action.res_model
                views = action.sudo().views
            model = self.env[model_name].with_user(user)
            self.assertTrue(model.has_access("read"), menu.complete_name)
            model.get_views(views)
