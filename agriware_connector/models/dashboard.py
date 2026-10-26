from odoo import api, fields, models


class AgriwareDashboard(models.TransientModel):
    _name = "agriware.dashboard"
    _description = "AgriWare Connector Dashboard"

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
        "agriware.wms.transaction", compute="_compute_recent_transactions",
        groups="agriware_connector.group_agriware_administrator",
    )

    @api.depends_context("allowed_company_ids")
    def _compute_recent_transactions(self):
        records = self.env["agriware.wms.transaction"].search(
            [("company_id", "in", self.env.companies.ids), ("picking_id.state", "=", "done")],
            order="create_date desc, id desc", limit=5,
        )
        for dashboard in self:
            dashboard.recent_transaction_ids = records

    @api.depends_context("allowed_company_ids")
    def _compute_metrics(self):
        company_ids = self.env.companies.ids
        ExternalSystem = self.env["agriware.external.system"].sudo()
        ApiKey = self.env["agriware.api.key"].sudo()
        Transaction = self.env["agriware.wms.transaction"].sudo()
        Import = self.env["agriware.inventory.import"].sudo()
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
            dashboard.mapping_count = self.env["agriware.external.id.mapping"].sudo().search_count(domain)
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
        return self._open_action("agriware_connector.action_agriware_suppliers")

    def action_open_inventory_imports(self):
        return self._open_action("agriware_connector.action_agriware_inventory_imports")
