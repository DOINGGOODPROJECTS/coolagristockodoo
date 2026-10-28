import math

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CoolAgristockExternalSystem(models.Model):
    _name = "cool_agristock.external.system"
    _description = "Cool Agristock External System"
    _order = "name"

    name = fields.Char(
        required=True,
        help="A human-readable name for this external system, "
             "e.g. 'Main Warehouse WMS'.",
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

    _code_company_uniq = models.Constraint(
        "unique(company_id, code)",
        "An external system with this code already exists for this company.",
    )

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
