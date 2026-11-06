import re
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CoolAgristockConnectionWizard(models.TransientModel):
    _name = "cool_agristock.connection.wizard"
    _description = "Add Cool Agristock Connection"

    name = fields.Char(
        string="Connection Name",
        required=True,
        help="Your own label for this connection, e.g. 'Main Agricultural "
             "Warehouse'.",
    )

    wms_name = fields.Char(
        string="WMS Name",
        required=True,
        help="The external warehouse management system this connection is "
             "for, e.g. 'Cool Agristock WMS', 'SAP WMS', 'Custom WMS'.",
    )

    description = fields.Text()

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    expiration_preset = fields.Selection(
        [
            ("30", "30 days"),
            ("90", "90 days"),
            ("365", "1 year"),
            ("never", "Never expires"),
            ("custom", "Custom expiration date"),
        ],
        string="Expiration",
        default="90",
        required=True,
    )

    expiration_date = fields.Datetime(
        string="Custom Expiration Date",
        help="Only used when Expiration is set to 'Custom expiration date'.",
    )

    api_base_url = fields.Char(
        string="API Base URL", compute="_compute_advanced_info",
    )

    auth_header_example = fields.Char(
        string="Authorization Header", compute="_compute_advanced_info",
    )

    @api.depends_context("uid")
    def _compute_advanced_info(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", ""
        )
        for record in self:
            record.api_base_url = f"{base_url}/cool_agristock/api/v1"
            record.auth_header_example = "Authorization: Bearer <API key>"

    @api.onchange("expiration_preset")
    def _onchange_expiration_preset(self):
        if self.expiration_preset != "custom":
            self.expiration_date = False

    def _generate_unique_code(self):
        """Derive a short, stable, unique-per-company code from the
        connection name, matching external_system.code's own documented
        purpose (external ID mappings are scoped to this code)."""
        self.ensure_one()

        base = re.sub(r"[^a-z0-9]+", "_", (self.name or "").strip().lower()).strip("_")
        base = base[:40] or "connection"

        ExternalSystem = self.env["cool_agristock.external.system"]
        code = base
        suffix = 1
        while ExternalSystem.search_count([
            ("company_id", "=", self.company_id.id), ("code", "=", code),
        ]):
            suffix += 1
            code = f"{base}_{suffix}"

        return code

    def action_generate(self):
        self.ensure_one()

        if self.expiration_preset == "never":
            expiration = False
        elif self.expiration_preset == "custom":
            if not self.expiration_date:
                raise UserError(_(
                    "Set a custom expiration date, or choose a different "
                    "expiration option."
                ))
            if self.expiration_date <= fields.Datetime.now():
                raise UserError(_(
                    "The expiration date must be in the future."
                ))
            expiration = self.expiration_date
        else:
            expiration = fields.Datetime.now() + timedelta(days=int(self.expiration_preset))

        external_system = self.env["cool_agristock.external.system"].create({
            "name": self.name,
            "wms_name": self.wms_name,
            "description": self.description,
            "company_id": self.company_id.id,
            "code": self._generate_unique_code(),
        })

        raw_key, _record = self.env["cool_agristock.api.key"].generate_key(
            name=self.name,
            company=self.company_id,
            expiration_date=expiration,
            external_system=external_system,
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.show",
            "name": _("API Key Ready"),
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_key": raw_key},
        }
