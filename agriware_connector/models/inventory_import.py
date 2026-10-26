import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class AgriwareInventoryImport(models.Model):
    _name = "agriware.inventory.import"
    _description = "AgriWare Inventory Import Batch"
    _order = "submitted_at desc"
    _rec_name = "external_reference"

    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )

    external_system_id = fields.Many2one(
        "agriware.external.system", string="External System",
        required=True, ondelete="restrict",
    )

    external_reference = fields.Char(
        required=True,
        help="The WMS's own identifier for this stock-observation batch, "
             "e.g. 'INITIAL-2026-001'. Together with company_id and "
             "external_system_id, this is the import's identity -- see "
             "the unique constraint below.",
    )

    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, ondelete="restrict",
    )

    location_id = fields.Many2one(
        "stock.location", required=True, ondelete="restrict",
        help="The single stock location this import's quantities were "
             "compared against -- always warehouse_id.lot_stock_id in "
             "this phase (see docs/INITIAL_INVENTORY_IMPORT.md's "
             "Location mapping section for why only that one location "
             "is supported).",
    )

    request_hash = fields.Char(
        required=True,
        help="SHA-256 of the normalized request body. Lets a retried "
             "POST with identical content be recognized as the same "
             "import (idempotent) rather than a conflicting reuse of "
             "the same external_reference.",
    )

    state = fields.Selection([
        ("pending_review", "Pending Review"),
        ("stale", "Stale -- Needs Re-Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("applied", "Applied Automatically"),
    ], default="pending_review", required=True)

    submitted_at = fields.Datetime(required=True, default=fields.Datetime.now)
    submitted_by = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        help="The integration user the authenticated API key resolved "
             "to at submission time.",
    )

    reviewed_by = fields.Many2one("res.users", readonly=True)
    reviewed_at = fields.Datetime(readonly=True)
    applied_by = fields.Many2one("res.users", readonly=True)
    applied_at = fields.Datetime(readonly=True)

    notes = fields.Text()

    line_ids = fields.One2many(
        "agriware.inventory.import.line", "import_id", string="Lines",
    )

    _external_reference_uniq = models.Constraint(
        "unique(company_id, external_system_id, external_reference)",
        "This external_reference has already been used for an "
        "inventory import, for this company and external system.",
    )

    # -- Authorization ------------------------------------------------------

    def _check_review_access(self):
        """Approving or rejecting a staged inventory import is an
        inventory-management decision, not an API-integration action --
        reuse Odoo's own native Inventory Manager group rather than
        inventing a parallel concept of authorization for it.
        """
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(_(
                "Only Inventory Managers may approve or reject inventory imports."
            ))

    def _check_recalculate_access(self):
        if not self.env.user.has_group("stock.group_stock_user"):
            raise AccessError(_(
                "Only Inventory users may inspect inventory imports."
            ))

    # -- Review actions -------------------------------------------------------

    def _recompute_lines(self):
        """Re-read the live on-hand quantity for every line of this single
        import and refresh current_odoo_quantity/proposed_difference.

        :returns: True if any line's live quantity differs (outside its
            UOM's own rounding) from the value last recorded for it --
            i.e. the import is stale and must not be approved as-is.
        """
        self.ensure_one()
        went_stale = False
        for line in self.line_ids:
            fresh_qty = line._read_onhand_quantity()
            changed = float_compare(
                fresh_qty, line.current_odoo_quantity,
                precision_rounding=line.uom_id.rounding or 0.01,
            ) != 0
            line.write({
                "current_odoo_quantity": fresh_qty,
                "proposed_difference": line.reported_quantity - fresh_qty,
                "validation_status": "stale" if changed else "ok",
            })
            went_stale = went_stale or changed
        return went_stale

    def action_recalculate(self):
        """Refresh every line's reconciliation against current Odoo stock.
        Available to any inventory user -- this only ever reads data and
        moves a stale import back to pending_review once its numbers are
        current again; it never approves anything by itself.
        """
        for record in self:
            record._check_recalculate_access()
            if record.state not in ("pending_review", "stale"):
                continue
            if record._recompute_lines():
                record.state = "stale"
            elif record.state == "stale":
                record.state = "pending_review"

    def action_approve(self):
        """Mark this staged import as approved.

        This NEVER touches stock.quant.quantity, never calls
        action_apply_inventory(), and never creates a stock move --
        approval only records that an authorized Inventory Manager has
        reviewed the discrepancy and wants it acted on. Applying it to
        real stock remains a separate, manual step in Odoo's own native
        Inventory Adjustment screen -- see docs/INITIAL_INVENTORY_IMPORT.md's
        "Native adjustment handoff" section for why that handoff isn't
        automated in this phase.

        Re-checks live stock before approving: if anything changed since
        this import's numbers were last computed, it is flipped to
        'stale' instead of approved, and the reviewer must look again
        (Phase 12's "require renewed human review").
        """
        self._check_review_access()
        for record in self:
            if record.state not in ("pending_review", "stale"):
                raise UserError(_(
                    "Only a pending or stale import can be approved."
                ))
            if record._recompute_lines():
                record.state = "stale"
            else:
                record.state = "approved"
                record.reviewed_by = self.env.user
                record.reviewed_at = fields.Datetime.now()

    def action_reject(self):
        self._check_review_access()
        for record in self:
            if record.state not in ("pending_review", "stale"):
                raise UserError(_(
                    "Only a pending or stale import can be rejected."
                ))
            record.state = "rejected"
            record.reviewed_by = self.env.user
            record.reviewed_at = fields.Datetime.now()

    def _apply_from_api(self, external_system, api_user):
        """Apply a WMS count as an Odoo inventory adjustment atomically.

        This private method is only called by the authenticated API route.
        It rechecks the stock snapshot, rejects quantities split across
        owners/packages (not represented by this API contract), then uses
        Odoo's native quant inventory workflow to create the stock moves.
        """
        self.ensure_one()
        if not api_user.has_group("agriware_connector.group_agriware_api_user"):
            raise AccessError(_("Only AgriWare API Users can apply WMS inventory counts."))
        if (
            self.external_system_id != external_system
            or self.company_id != external_system.company_id
            or self.submitted_by != api_user
            or not external_system.active
        ):
            raise AccessError(_("The external system is not authorized for this import."))
        if (
            not external_system.allow_automatic_inventory_adjustments
            or external_system.max_auto_inventory_delta <= 0
        ):
            raise AccessError(_(
                "Automatic inventory adjustments are not enabled for this external system."
            ))
        if self.state != "pending_review":
            raise UserError(_("Only a new inventory import can be applied automatically."))

        Quant = self.env["stock.quant"].sudo().with_company(self.company_id)
        for line in self.line_ids:
            current_qty = line._read_onhand_quantity()
            if float_compare(
                current_qty, line.current_odoo_quantity,
                precision_rounding=line.uom_id.rounding or 0.01,
            ) != 0:
                raise UserError(_(
                    "Stock changed while this request was being processed. "
                    "Submit a fresh count using a new external_reference."
                ))
            if abs(line.reported_quantity - current_qty) > external_system.max_auto_inventory_delta:
                raise UserError(_(
                    "Inventory variance exceeds the external system's configured limit."
                ))

            domain = [
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", line.location_id.id),
                ("lot_id", "=", line.lot_id.id or False),
            ]
            quants = Quant.search(domain)
            if any(quant.package_id or quant.owner_id for quant in quants):
                raise UserError(_(
                    "Automatic adjustment is not supported for stock assigned "
                    "to a package or owner."
                ))
            if len(quants) > 1 or any(quants.mapped("inventory_quantity_set")):
                raise UserError(_(
                    "Automatic adjustment requires one unambiguous stock quantity "
                    "with no pending manual count. Review this stock in Odoo first."
                ))
            quant = quants[:1]
            quant_model = Quant.with_context(inventory_mode=True)
            if quant:
                quant_model.browse(quant.id).write({
                    "inventory_quantity_auto_apply": line.reported_quantity,
                })
            else:
                quant_model.create({
                    "product_id": line.product_id.id,
                    "location_id": line.location_id.id,
                    "lot_id": line.lot_id.id or False,
                    "inventory_quantity_auto_apply": line.reported_quantity,
                })

        self.write({
            "state": "applied",
            "applied_by": api_user.id,
            "applied_at": fields.Datetime.now(),
        })


class AgriwareInventoryImportLine(models.Model):
    _name = "agriware.inventory.import.line"
    _description = "AgriWare Inventory Import Line"
    _order = "id"

    import_id = fields.Many2one(
        "agriware.inventory.import", required=True, ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product", required=True, ondelete="restrict",
    )

    location_id = fields.Many2one(
        "stock.location", required=True, ondelete="restrict",
    )

    lot_id = fields.Many2one(
        "stock.lot", ondelete="restrict",
        help="Set only for a lot/serial-tracked product (Phase F). "
             "Reconciliation for such a line is scoped to the exact "
             "(product_id, location_id, lot_id) combination -- never "
             "aggregated with any other lot of the same product.",
    )

    uom_id = fields.Many2one(
        "uom.uom", required=True,
        help="The product's own unit of measure. reported_quantity and "
             "current_odoo_quantity are both expressed in this unit, "
             "never in external_unit_code's unit directly.",
    )

    external_unit_code = fields.Char(
        required=True,
        help="The WMS's own unit code exactly as submitted (e.g. "
             "'bag_50kg'), preserved for audit even after normalization.",
    )

    original_reported_quantity = fields.Float(
        required=True, digits="Product Unit",
        help="The quantity exactly as submitted by the WMS, in "
             "external_unit_code, before UOM normalization.",
    )

    reported_quantity = fields.Float(
        required=True, digits="Product Unit",
        help="original_reported_quantity, converted into uom_id.",
    )

    current_odoo_quantity = fields.Float(
        required=True, digits="Product Unit",
        help="The on-hand quantity (stock.quant.quantity, summed, "
             "read-only) Odoo reported for this product at location_id "
             "the last time this line was (re)computed.",
    )

    proposed_difference = fields.Float(
        required=True, digits="Product Unit",
        help="reported_quantity - current_odoo_quantity, as of the last "
             "(re)computation. Never applied automatically.",
    )

    validation_status = fields.Selection([
        ("ok", "OK"),
        ("stale", "Stale"),
    ], default="ok", required=True)

    error_message = fields.Char(
        help="Reserved for a future partial-validation mode. This phase "
             "validates an entire import atomically before any line is "
             "ever stored, so this is always empty today.",
    )

    def _read_onhand_quantity(self):
        """Read-only. Sums stock.quant.quantity for this line's exact
        (product_id, location_id[, lot_id]) -- never writes
        inventory_quantity, never calls action_apply_inventory().

        When lot_id is set (Phase F), the domain is scoped to that
        exact lot as well, so a lot-tracked line is never reconciled
        against -- or confused with -- a different lot of the same
        product sitting in the same location.
        """
        self.ensure_one()
        domain = [
            ("product_id", "=", self.product_id.id),
            ("location_id", "=", self.location_id.id),
        ]
        if self.lot_id:
            domain.append(("lot_id", "=", self.lot_id.id))
        quants = self.env["stock.quant"].sudo().search(domain)
        return sum(quants.mapped("quantity"))
