from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class CoolAgristockUomMapping(models.Model):
    _name = "cool_agristock.uom.mapping"
    _description = "Cool Agristock Unit of Measure Mapping"
    _order = "external_unit_code"
    _rec_name = "external_unit_code"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    external_system_id = fields.Many2one(
        "cool_agristock.external.system",
        string="External System",
        required=True,
        ondelete="restrict",
    )

    external_unit_code = fields.Char(
        string="External Unit Code",
        required=True,
        help="The WMS's own unit code, e.g. 'bag_50kg' or 'carton_20'. "
             "Free text -- not restricted to any fixed list, since "
             "different WMS systems name their units differently.",
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Odoo Unit of Measure",
        required=True,
        help="An existing Odoo unit of measure this external code maps "
             "to. This module never creates or guesses a conversion "
             "factor -- it only references a UOM the installation "
             "already has, with whatever factor was configured for it "
             "in Odoo itself (Settings > Technical > Units of Measure).",
    )

    active = fields.Boolean(default=True)

    description = fields.Text(
        help="Free-text notes, e.g. clarifying that 'bag' means a "
             "specific product's 50kg packaging and does not apply to "
             "every product using this code.",
    )

    _external_unit_code_uniq = models.Constraint(
        "unique(company_id, external_system_id, external_unit_code)",
        "This external unit code is already mapped for this company "
        "and external system.",
    )

    @api.constrains("external_unit_code")
    def _check_external_unit_code(self):
        for record in self:
            if not record.external_unit_code or not record.external_unit_code.strip():
                raise ValidationError(_(
                    "The external unit code cannot be empty."
                ))

    @api.constrains("company_id", "external_system_id")
    def _check_external_system_company(self):
        for record in self:
            if record.external_system_id.company_id != record.company_id:
                raise ValidationError(_(
                    "The external system must belong to the same "
                    "company as the UOM mapping."
                ))

    @api.model
    def resolve_unit(self, company, external_system, external_unit_code):
        """Look up the Odoo uom.uom for an external unit code, scoped to
        (company, external_system). Read-only; returns an empty
        ``uom.uom`` recordset if no active mapping exists -- callers
        should fall back to any other supported-unit mechanism, or
        reject the request, rather than guessing.
        """
        if company not in self.env.user.company_ids:
            raise AccessError(_("You do not have access to this company."))

        mapping = self.sudo().search([
            ("company_id", "=", company.id),
            ("external_system_id", "=", external_system.id),
            ("external_unit_code", "=", external_unit_code),
            ("active", "=", True),
        ], limit=1)

        return mapping.uom_id
