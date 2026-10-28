import logging

import psycopg2

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)

# Explicit allow-list: no API client may address a mapping to a model
# outside this list. product.template is deliberately excluded -- every
# existing and planned product-facing endpoint (GET /products today,
# POST/PATCH /products in a future phase) operates on product.product,
# the sellable/stockable variant, matching the model the REST layer
# already reads from.
ALLOWED_MODELS = (
    "product.product",
    "stock.warehouse",
    "res.partner",
    "stock.lot",
    "stock.location",
)


class CoolAgristockExternalIdMapping(models.Model):
    _name = "cool_agristock.external.id.mapping"
    _description = "Cool Agristock External ID Mapping"
    _order = "create_date desc"
    _rec_name = "external_id"

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

    res_model = fields.Char(
        string="Model",
        required=True,
        help="The Odoo model this mapping targets, e.g. 'product.product'. "
             "Restricted to an explicit allow-list -- see ALLOWED_MODELS.",
    )

    external_id = fields.Char(
        string="External ID",
        required=True,
        help="The external system's own identifier for this record, "
             "e.g. 'WMS-PRODUCT-001'.",
    )

    res_id = fields.Integer(
        string="Record ID",
        required=True,
        help="The id of the record in res_model that external_id maps to.",
    )

    _external_id_uniq = models.Constraint(
        "unique(company_id, external_system_id, res_model, external_id)",
        "This external ID is already mapped to a record for this company "
        "and external system.",
    )

    _res_id_uniq = models.Constraint(
        "unique(company_id, external_system_id, res_model, res_id)",
        "This record is already mapped to a different external ID for "
        "this company and external system.",
    )

    def action_open_record(self):
        self.ensure_one()
        self.check_access("read")
        if self.res_model not in ALLOWED_MODELS:
            raise UserError(_("Unsupported mapped record type."))
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_("The mapped Odoo record no longer exists."))
        record.check_access("read")
        return {
            "type": "ir.actions.act_window", "name": record.display_name,
            "res_model": self.res_model, "res_id": record.id,
            "view_mode": "form", "target": "current",
        }

    @api.constrains("res_model")
    def _check_res_model(self):
        for record in self:
            if record.res_model not in ALLOWED_MODELS:
                raise ValidationError(_(
                    "Unsupported model for external ID mapping: %s"
                ) % record.res_model)

    @api.constrains("external_id")
    def _check_external_id(self):
        for record in self:
            if not record.external_id or not record.external_id.strip():
                raise ValidationError(_("external_id cannot be empty."))

    @api.constrains("company_id", "external_system_id")
    def _check_external_system_company(self):
        for record in self:
            if record.external_system_id.company_id != record.company_id:
                raise ValidationError(_(
                    "The external system must belong to the same company "
                    "as the mapping."
                ))

    @api.constrains("company_id", "res_model", "res_id")
    def _check_target_record(self):
        # Runs with sudo() deliberately: validating that a *target*
        # record exists and belongs to the right company is a system
        # invariant, not a per-user permission check -- the caller-level
        # authorization happens in _check_mapping_access() below, before any
        # record of this model is created or written in the first place.
        for record in self:
            target = self.env[record.res_model].sudo().browse(record.res_id)
            if not target.exists():
                raise ValidationError(_("The mapped record does not exist."))
            if "company_id" in target._fields:
                target_company = target.company_id
                if target_company and target_company != record.company_id:
                    raise ValidationError(_(
                        "The mapped record belongs to a different company."
                    ))

    # -- Authorization ----------------------------------------------------

    def _check_mapping_access(self, company):
        """Raise unless the current user may manage external ID mappings
        for ``company``.

        This mirrors the pattern already used by ``cool_agristock.api.key``'s
        ``_check_can_manage()``: callers of the mapping service (future
        REST controllers) are expected to authenticate via a Bearer API
        key and already pass the Cool Agristock API User group check at the
        HTTP layer, but this method re-validates it independently so the
        mapping service itself never silently trusts a sudo'd caller.
        """
        api_group = self.env.ref(
            "cool_agristock.group_cool_agristock_api_user"
        )

        if api_group not in self.env.user.all_group_ids:
            raise AccessError(_(
                "Only Cool Agristock API Users can manage external ID mappings."
            ))

        if company not in self.env.user.company_ids:
            raise AccessError(_(
                "You do not have access to this company."
            ))

    # -- Mapping service ----------------------------------------------------

    @api.model
    def resolve_mapping(self, company, external_system, res_model, external_id):
        """Look up an existing mapping. Read-only.

        :returns: the matching ``cool_agristock.external.id.mapping`` record,
            or an empty recordset if none exists.
        """
        if company not in self.env.user.company_ids:
            raise AccessError(_("You do not have access to this company."))

        return self.sudo().search([
            ("company_id", "=", company.id),
            ("external_system_id", "=", external_system.id),
            ("res_model", "=", res_model),
            ("external_id", "=", external_id),
        ], limit=1)

    @api.model
    def create_mapping(self, company, external_system, res_model, external_id, res_id):
        """Create a new mapping for ``external_id`` -> ``res_id``.

        The pre-check below handles the common case cheaply; the unique
        database constraints are the final concurrency safety net for
        two requests racing to map the same external_id at the same time
        -- not just this application-level check.

        :returns: tuple ``(mapping_record, created)``. ``created`` is
            ``False`` when ``external_id`` was already mapped (by this
            request losing a race, or simply because it already existed);
            the caller should treat that the same way receipt/dispatch
            creation treats a duplicate external_reference (HTTP 409,
            once this is wired to a controller).
        """
        self._check_mapping_access(company)

        if res_model not in ALLOWED_MODELS:
            raise ValidationError(_(
                "Unsupported model for external ID mapping: %s"
            ) % res_model)

        existing = self.resolve_mapping(
            company, external_system, res_model, external_id
        )
        if existing:
            return existing, False

        try:
            with self.env.cr.savepoint():
                record = self.sudo().create({
                    "company_id": company.id,
                    "external_system_id": external_system.id,
                    "res_model": res_model,
                    "external_id": external_id,
                    "res_id": res_id,
                })
            return record, True
        except psycopg2.IntegrityError:
            # Lost a race against a concurrent request for the same
            # identity. The savepoint rollback above already undid our
            # own failed insert; the other request's row is now the
            # source of truth.
            existing = self.resolve_mapping(
                company, external_system, res_model, external_id
            )
            if not existing:
                # The unique constraint fired for some other reason
                # (e.g. the res_id uniqueness one) -- re-raise rather
                # than silently returning nothing.
                raise
            return existing, False

    @api.model
    def update_mapping(self, company, external_system, res_model, external_id, res_id):
        """Re-point an existing mapping at a different Odoo record id.

        Raises if no mapping exists for this identity -- this method
        never creates one (mirrors PATCH semantics: it only acts on
        records that already exist).
        """
        self._check_mapping_access(company)

        mapping = self.resolve_mapping(
            company, external_system, res_model, external_id
        )
        if not mapping:
            raise ValidationError(_(
                "No mapping exists for this external_id."
            ))

        mapping.sudo().write({"res_id": res_id})
        return mapping

    @api.model
    def remove_mapping(self, company, external_system, res_model, external_id):
        """Delete a mapping (the mapping row only -- never the underlying
        Odoo record itself).

        :returns: ``True`` if a mapping was found and removed, ``False``
            if none existed (idempotent: removing a non-existent mapping
            is not an error).
        """
        self._check_mapping_access(company)

        mapping = self.resolve_mapping(
            company, external_system, res_model, external_id
        )
        if not mapping:
            return False

        mapping.sudo().unlink()
        return True
