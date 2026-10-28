from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    cool_agristock_is_supplier = fields.Boolean(
        string="Cool Agristock Supplier",
        help="Identifies contacts managed as suppliers by a Cool Agristock WMS.",
        index=True,
    )
