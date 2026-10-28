from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CoolAgristockApiKeyGenerateWizard(models.TransientModel):
    _name = "cool_agristock.api.key.generate.wizard"
    _description = "Generate Cool Agristock API Key"

    name = fields.Char(
        string="Integration Name",
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    external_system_id = fields.Many2one(
        "cool_agristock.external.system",
        string="Authorized External System",
        domain="[('company_id', '=', company_id)]",
        help="Optional. Binding this key to an external system "
             "authorizes it for write operations that require one (e.g. "
             "product synchronization). Leave empty for a key that only "
             "needs read access or receipt/dispatch operations -- those "
             "are unaffected either way.",
    )

    never_expires = fields.Boolean(
        string="Never Expires",
    )

    expiration_date = fields.Datetime(
        string="Expiration Date",
    )

    @api.onchange("never_expires")
    def _onchange_never_expires(self):
        if self.never_expires:
            self.expiration_date = False

    def action_generate(self):
        self.ensure_one()

        if not self.never_expires:
            if not self.expiration_date:
                raise UserError(_(
                    "Set an expiration date, or choose Never Expires."
                ))
            if self.expiration_date <= fields.Datetime.now():
                raise UserError(_(
                    "The expiration date must be in the future."
                ))

        expiration = False if self.never_expires else self.expiration_date

        raw_key, _record = self.env["cool_agristock.api.key"].generate_key(
            name=self.name,
            company=self.company_id,
            expiration_date=expiration,
            external_system=self.external_system_id or None,
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.show",
            "name": _("API Key Ready"),
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_key": raw_key},
        }
