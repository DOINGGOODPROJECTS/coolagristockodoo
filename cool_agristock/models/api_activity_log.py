import uuid
from datetime import timedelta

from odoo import api, fields, models


class CoolAgristockApiActivityLog(models.Model):
    _name = "cool_agristock.api.activity.log"
    _description = "Cool Agristock API Activity Log"
    _order = "create_date desc"
    _rec_name = "endpoint"

    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
    )

    external_system_id = fields.Many2one(
        "cool_agristock.external.system", string="Connection",
        index=True,
        help="Set only when the authenticated API key is bound to an "
             "external system. Unbound keys still log activity here, just "
             "without a connection to attribute it to.",
    )

    api_key_id = fields.Many2one(
        "cool_agristock.api.key", string="API Key", index=True,
    )

    endpoint = fields.Char(
        required=True,
        help="e.g. 'GET /cool_agristock/api/v1/products'.",
    )

    http_status = fields.Integer(required=True)

    success = fields.Boolean(compute="_compute_success", store=True)

    error_category = fields.Selection(
        [
            ("auth_failed", "Authentication Failed"),
            ("validation_error", "Validation Error"),
            ("not_found", "Not Found"),
            ("conflict", "Conflict"),
            ("server_error", "Server Error"),
        ],
        string="Error Category",
    )

    request_id = fields.Char(
        string="Request ID", default=lambda self: uuid.uuid4().hex,
        help="Correlates this log entry with the server log line for the "
             "same request.",
    )

    @api.depends("http_status")
    def _compute_success(self):
        for record in self:
            record.success = bool(record.http_status) and record.http_status < 400

    @api.model
    def _log(self, endpoint, http_status, external_system=None, api_key=None,
              error_category=None, company=None):
        """Record one API activity entry.

        System-generated only -- always sudo()'d, never exposed as a
        user-facing create. Never pass request headers, bodies, or key
        material here: only metadata about the call.
        """
        self.sudo().create({
            "company_id": (company or self.env.company).id,
            "external_system_id": external_system.id if external_system else False,
            "api_key_id": api_key.id if api_key else False,
            "endpoint": endpoint,
            "http_status": http_status,
            "error_category": error_category,
        })

    @api.autovacuum
    def _gc_activity_log(self):
        """Daily retention sweep, run automatically by Odoo's own
        'Base: Auto-vacuum internal data' cron. Keeps this table from
        growing without bound."""
        retention_days = int(self.env["ir.config_parameter"].sudo().get_param(
            "cool_agristock.activity_log_retention_days", "90"
        ))
        cutoff = fields.Datetime.now() - timedelta(days=retention_days)
        self.sudo().search([("create_date", "<", cutoff)]).unlink()
