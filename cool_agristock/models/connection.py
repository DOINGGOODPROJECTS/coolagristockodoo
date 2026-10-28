from odoo import models, fields, _
from odoo.exceptions import UserError


class CoolAgristockConnection(models.Model):
    _name = "cool_agristock.connection"
    _description = "Cool Agristock WMS Connection"

    name = fields.Char(
        string="WMS Name",
        required=True,
    )

    api_url = fields.Char(
        string="WMS API URL",
        required=True,
    )

    api_key = fields.Char(
        string="API Key",
        groups="base.group_system",
        copy=False,
    )

    status = fields.Selection(
        [
            ("disconnected", "Disconnected"),
            ("connected", "Connected"),
        ],
        string="Connection Status",
        default="disconnected",
        readonly=True,
    )

    def action_test_connection(self):
        raise UserError(
            _(
                "Connection testing is not implemented yet. "
                "The REST API client will be added in the next step."
            )
        )
