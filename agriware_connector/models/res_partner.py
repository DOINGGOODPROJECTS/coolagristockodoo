from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    agriware_is_supplier = fields.Boolean(
        string="AgriWare Supplier",
        help="Identifies contacts managed as suppliers by an AgriWare WMS.",
        index=True,
    )
