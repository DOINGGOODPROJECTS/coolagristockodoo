import math

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class CoolAgristockExternalSystem(models.Model):
    _name = "cool_agristock.external.system"
    _description = "Cool Agristock External System"
    _order = "name"

    name = fields.Char(
        required=True,
        help="A human-readable name for this external system, "
             "e.g. 'Main Warehouse WMS'. Shown in the Connections screen as "
             "'Connection Name'.",
    )

    wms_name = fields.Char(
        string="WMS Name",
        help="The external warehouse management system this connection is "
             "for, e.g. 'SAP WMS', 'NetSuite', 'Custom WMS'. Distinct from "
             "the connection's own label above -- optional, purely "
             "descriptive.",
    )

    code = fields.Char(
        required=True,
        help="A short, stable identifier for this external system, "
             "e.g. 'primary_wms'. External ID mappings are scoped to "
             "this code, not to any specific API key, so rotating or "
             "replacing an API key never orphans existing mappings.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(default=True)

    allow_automatic_inventory_adjustments = fields.Boolean(
        string="Allow automatic inventory adjustments",
        default=False,
        help="When enabled, this WMS may use the dedicated API apply endpoint. "
             "The endpoint still enforces the configured maximum variance.",
    )

    max_auto_inventory_delta = fields.Float(
        string="Maximum automatic inventory variance",
        default=0.0,
        help="Maximum absolute quantity difference per product/lot line, "
             "in the product's Odoo unit of measure. Must be greater than "
             "zero before automatic adjustments can be enabled.",
    )

    description = fields.Text()

    api_key_ids = fields.One2many(
        "cool_agristock.api.key", "external_system_id",
        string="API Keys",
    )

    active_api_key_count = fields.Integer(
        string="Active API Keys", compute="_compute_key_stats",
    )

    primary_api_key_id = fields.Many2one(
        "cool_agristock.api.key", string="Primary API Key",
        compute="_compute_key_stats",
        help="The most recently created active API key for this "
             "connection, shown (masked) on the Connections list.",
    )

    next_key_expiration = fields.Datetime(
        string="Expiration", compute="_compute_key_stats",
        help="The soonest expiration date among this connection's active "
             "API keys. Empty if every active key never expires, or there "
             "is no active key.",
    )

    last_activity_at = fields.Datetime(
        string="Last Activity", compute="_compute_last_activity",
        help="Timestamp of the most recent authenticated API request from "
             "this connection, from the Cool Agristock activity log. Empty "
             "if this connection has never been used to call the API.",
    )

    last_successful_sync_at = fields.Datetime(
        string="Last Successful Sync", compute="_compute_last_successful_sync",
        help="Timestamp of the most recent completed receipt or dispatch "
             "recorded for this connection.",
    )

    connection_status = fields.Selection(
        [
            ("active", "Active"),
            ("awaiting_first_connection", "Awaiting First Connection"),
            ("no_active_key", "No Active Key"),
            ("inactive", "Inactive"),
        ],
        string="Status", compute="_compute_connection_status",
        help="Active: enabled, has an active API key, and has received at "
             "least one authenticated request. Awaiting First Connection: "
             "enabled and has an active key, but the external WMS has not "
             "called the API yet. No Active Key: enabled but every API key "
             "is missing, expired, or revoked. Inactive: this connection "
             "has been disabled.",
    )

    _code_company_uniq = models.Constraint(
        "unique(company_id, code)",
        "An external system with this code already exists for this company.",
    )

    @api.depends("api_key_ids.revoked_date", "api_key_ids.expiration_date", "api_key_ids.apikey_id")
    def _compute_key_stats(self):
        for record in self:
            active_keys = record.api_key_ids.filtered(lambda k: k.state == "active")
            record.active_api_key_count = len(active_keys)
            record.primary_api_key_id = active_keys[:1]
            expirations = active_keys.filtered("expiration_date").mapped("expiration_date")
            record.next_key_expiration = min(expirations) if expirations else False

    @api.depends_context("allowed_company_ids")
    def _compute_last_activity(self):
        Log = self.env["cool_agristock.api.activity.log"].sudo()
        for record in self:
            last = Log.search(
                [("external_system_id", "=", record.id)],
                order="create_date desc", limit=1,
            )
            record.last_activity_at = last.create_date if last else False

    @api.depends_context("allowed_company_ids")
    def _compute_last_successful_sync(self):
        Transaction = self.env["cool_agristock.wms.transaction"].sudo()
        for record in self:
            last = Transaction.search(
                [("external_system_id", "=", record.id), ("picking_id.state", "=", "done")],
                order="create_date desc", limit=1,
            )
            record.last_successful_sync_at = last.create_date if last else False

    @api.depends("active", "active_api_key_count", "last_activity_at")
    def _compute_connection_status(self):
        for record in self:
            if not record.active:
                record.connection_status = "inactive"
            elif not record.active_api_key_count:
                record.connection_status = "no_active_key"
            elif not record.last_activity_at:
                record.connection_status = "awaiting_first_connection"
            else:
                record.connection_status = "active"

    def _check_can_manage(self):
        """Raise unless the current user is a Cool Agristock Administrator
        for every record's company. Mirrors
        cool_agristock.api.key._check_can_manage()."""
        admin_group = self.env.ref(
            "cool_agristock.group_cool_agristock_administrator"
        )

        if admin_group not in self.env.user.all_group_ids:
            raise AccessError(_(
                "Only Cool Agristock Administrators can manage connections."
            ))

        for record_company in self.mapped("company_id"):
            if record_company not in self.env.user.company_ids:
                raise AccessError(_(
                    "You do not have access to connections for this company."
                ))

    def action_activate(self):
        self._check_can_manage()
        self.write({"active": True})

    def action_deactivate(self):
        self._check_can_manage()
        self.write({"active": False})

    def action_open_api_keys(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cool_agristock.action_cool_agristock_api_keys"
        )
        action["domain"] = [("external_system_id", "=", self.id)]
        action["context"] = {"default_external_system_id": self.id}
        return action

    def action_open_activity(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Activity: %s") % self.name,
            "res_model": "cool_agristock.api.activity.log",
            "view_mode": "list,form",
            "domain": [("external_system_id", "=", self.id)],
        }

    def action_test_connection(self):
        """Honest, inbound-appropriate connection test.

        Cool Agristock's REST API is inbound-only: the external WMS calls
        Odoo, Odoo never calls out to the WMS. There is nothing to "ping"
        here. What this can genuinely verify is that the configuration on
        Odoo's side is ready for the external WMS to authenticate -- it
        never claims the external WMS is actually connected, since that
        can only be known once a real authenticated request arrives (see
        connection_status / last_activity_at).
        """
        self.ensure_one()
        self._check_can_manage()

        if not self.active:
            raise UserError(_(
                "This connection is inactive. Activate it before testing."
            ))

        active_keys = self.api_key_ids.filtered(lambda k: k.state == "active")
        if not active_keys:
            raise UserError(_(
                "This connection has no active API key. Generate one "
                "before testing."
            ))

        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", ""
        )

        message = _(
            "Configuration ready: %(count)s active API key(s).\n\n"
            "Have your external WMS call this endpoint with the issued key "
            "to confirm the connection:\n\n"
            "curl %(url)s/cool_agristock/api/v1/health "
            "-H \"Authorization: Bearer <API key>\"\n\n"
            "This connection will show as Active once a real authenticated "
            "request is received -- an active key alone does not mean the "
            "WMS is actually connected yet."
        ) % {"count": len(active_keys), "url": base_url}

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Ready to Test"),
                "message": message,
                "sticky": True,
                "type": "info",
            },
        }

    @api.constrains("code")
    def _check_code(self):
        for record in self:
            if not record.code or not record.code.strip():
                raise ValidationError(_(
                    "The external system code cannot be empty."
                ))

    @api.constrains("allow_automatic_inventory_adjustments", "max_auto_inventory_delta")
    def _check_automatic_inventory_variance(self):
        for record in self:
            if not math.isfinite(record.max_auto_inventory_delta) or (
                record.allow_automatic_inventory_adjustments
                and record.max_auto_inventory_delta <= 0
            ):
                raise ValidationError(_(
                    "Automatic adjustments require a finite, positive maximum variance."
                ))
