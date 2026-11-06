from odoo import api, fields, models


class CoolAgristockDashboard(models.TransientModel):
    _name = "cool_agristock.dashboard"
    _description = "Cool Agristock Dashboard"

    name = fields.Char(default="Overview")

    active_system_count = fields.Integer(compute="_compute_metrics")
    active_api_key_count = fields.Integer(compute="_compute_metrics")
    receipt_count = fields.Integer(compute="_compute_metrics")
    dispatch_count = fields.Integer(compute="_compute_metrics")
    completed_transaction_count = fields.Integer(compute="_compute_metrics")
    cancelled_transaction_count = fields.Integer(compute="_compute_metrics")
    pending_import_count = fields.Integer(compute="_compute_metrics")
    rejected_import_count = fields.Integer(compute="_compute_metrics")
    mapping_count = fields.Integer(compute="_compute_metrics")
    last_transaction_at = fields.Datetime(compute="_compute_metrics")

    recent_transaction_ids = fields.Many2many(
        "cool_agristock.wms.transaction", compute="_compute_recent_transactions",
        groups="cool_agristock.group_cool_agristock_administrator",
    )

    @api.depends_context("allowed_company_ids")
    def _compute_recent_transactions(self):
        records = self.env["cool_agristock.wms.transaction"].search(
            [("company_id", "in", self.env.companies.ids), ("picking_id.state", "=", "done")],
            order="create_date desc, id desc", limit=5,
        )
        for dashboard in self:
            dashboard.recent_transaction_ids = records

    @api.depends_context("allowed_company_ids")
    def _compute_metrics(self):
        company_ids = self.env.companies.ids
        ExternalSystem = self.env["cool_agristock.external.system"].sudo()
        ApiKey = self.env["cool_agristock.api.key"].sudo()
        Transaction = self.env["cool_agristock.wms.transaction"].sudo()
        Import = self.env["cool_agristock.inventory.import"].sudo()
        for dashboard in self:
            dashboard.active_system_count = ExternalSystem.search_count([
                ("company_id", "in", company_ids), ("active", "=", True),
            ])
            dashboard.active_api_key_count = ApiKey.search_count([
                ("company_id", "in", company_ids),
                ("apikey_id", "!=", False),
                ("revoked_date", "=", False),
                "|", ("expiration_date", "=", False),
                ("expiration_date", ">", fields.Datetime.now()),
            ])
            domain = [("company_id", "in", company_ids)]
            dashboard.receipt_count = Transaction.search_count(
                domain + [("transaction_type", "=", "receipt")]
            )
            dashboard.dispatch_count = Transaction.search_count(
                domain + [("transaction_type", "=", "dispatch")]
            )
            dashboard.completed_transaction_count = Transaction.search_count(
                domain + [("picking_id.state", "=", "done")]
            )
            dashboard.cancelled_transaction_count = Transaction.search_count(
                domain + [("picking_id.state", "=", "cancel")]
            )
            dashboard.pending_import_count = Import.search_count([
                ("company_id", "in", company_ids),
                ("state", "in", ("pending_review", "stale")),
            ])
            dashboard.rejected_import_count = Import.search_count(
                domain + [("state", "=", "rejected")]
            )
            dashboard.mapping_count = self.env["cool_agristock.external.id.mapping"].sudo().search_count(domain)
            latest = Transaction.search(domain, limit=1, order="create_date desc")
            dashboard.last_transaction_at = latest.create_date if latest else False

    def _open_action(self, xmlid):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id(xmlid)

    def action_open_products(self):
        return self._open_action("stock.product_template_action_product")

    def action_open_inventory(self):
        return self._open_action("stock.stock_quant_action")

    def action_open_warehouses(self):
        return self._open_action("stock.action_warehouse_form")

    def action_open_receipts(self):
        return self._open_action("stock.action_picking_tree_incoming")

    def action_open_dispatches(self):
        return self._open_action("stock.action_picking_tree_outgoing")

    def action_open_lots(self):
        return self._open_action("stock.action_product_production_lot_form")

    def action_open_suppliers(self):
        return self._open_action("cool_agristock.action_cool_agristock_suppliers")

    def action_open_inventory_imports(self):
        return self._open_action("cool_agristock.action_cool_agristock_inventory_imports")

    def action_open_pending_imports(self):
        action = self._open_action("cool_agristock.action_cool_agristock_inventory_imports")
        action["domain"] = [("state", "in", ("pending_review", "stale"))]
        return action

    def action_open_rejected_imports(self):
        action = self._open_action("cool_agristock.action_cool_agristock_inventory_imports")
        action["domain"] = [("state", "=", "rejected")]
        return action

    def action_open_connections(self):
        return self._open_action("cool_agristock.action_cool_agristock_external_systems")

    def action_open_mappings(self):
        return self._open_action("cool_agristock.action_cool_agristock_external_id_mappings")

    def action_open_completed_transactions(self):
        action = self._open_action("cool_agristock.action_cool_agristock_wms_transactions")
        action["domain"] = [("picking_id.state", "=", "done")]
        return action

    def action_open_cancelled_transactions(self):
        return self._open_action("cool_agristock.action_cool_agristock_cancelled_transactions")

    def action_open_activity_chart(self):
        """A real, interactive native chart: receipts vs. dispatches over
        time, from cool_agristock.wms.transaction -- the same company-
        scoped, picking-backed records the rest of this dashboard counts.
        Not a custom widget: Odoo's own graph view, fully drag/zoom/
        group-by/measure-switchable out of the box."""
        return self._open_action("cool_agristock.action_cool_agristock_activity_chart")

    def action_open_category_chart(self):
        """Real post-sync category distribution: product.template grouped
        by categ_id, the same categories cool_agristock's product sync
        get-or-creates from whatever the external WMS sends."""
        return self._open_action("cool_agristock.action_cool_agristock_category_chart")
