from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgriwareWmsTransaction(models.Model):
    _name = "agriware.wms.transaction"
    _description = "AgriWare WMS Transaction Identity"
    _order = "create_date desc"
    _rec_name = "external_reference"

    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )

    external_system_id = fields.Many2one(
        "agriware.external.system", string="External System",
        required=True, ondelete="restrict",
    )

    transaction_type = fields.Selection([
        ("receipt", "Receipt"),
        ("dispatch", "Dispatch"),
    ], required=True)

    external_reference = fields.Char(
        required=True,
        help="The WMS's own identifier for this transaction, e.g. "
             "'WMS-REC-001'. Together with company_id, external_system_id, "
             "and transaction_type, this is the transaction's identity.",
    )

    request_hash = fields.Char(
        required=True,
        help="SHA-256 of the normalized request body. Lets a retried "
             "POST with identical content be recognized as the same "
             "transaction (idempotent) rather than a conflicting reuse "
             "of the same external_reference -- same pattern as "
             "agriware.inventory.import.request_hash.",
    )

    picking_id = fields.Many2one(
        "stock.picking", required=True, ondelete="cascade",
    )

    picking_state = fields.Selection(related="picking_id.state", string="Operation Status")
    completed_at = fields.Datetime(related="picking_id.date_done", string="Completed On")

    _identity_uniq = models.Constraint(
        "unique(company_id, external_system_id, transaction_type, external_reference)",
        "This external_reference has already been used for this "
        "transaction type, for this company and external system.",
    )

    @api.constrains("company_id", "external_system_id")
    def _check_external_system_company(self):
        for record in self:
            if record.external_system_id.company_id != record.company_id:
                raise ValidationError(_(
                    "The external system must belong to the same company "
                    "as the transaction."
                ))
