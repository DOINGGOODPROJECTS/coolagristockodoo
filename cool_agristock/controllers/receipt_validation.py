import json
import logging
import math

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare
from .api_security import require_cool_agristock_api_user, resolve_authorized_external_system

_logger = logging.getLogger(__name__)


class CoolAgristockReceiptValidationAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    @http.route(
        "/cool_agristock/api/v1/receipts/<int:receipt_id>/validate",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def validate_receipt(self, receipt_id, **kwargs):

        authorization = request.httprequest.headers.get(
            "Authorization", ""
        )

        if not authorization.startswith("Bearer "):
            return self.json_response({
                "status": "error",
                "message": "Bearer token required",
            }, 401)

        if not require_cool_agristock_api_user():
            return self.json_response({
                "status": "error",
                "message": "Access denied: Cool Agristock API User role required",
            }, 403)

        try:
            payload = json.loads(
                request.httprequest.get_data(as_text=True)
            )
        except (ValueError, UnicodeDecodeError):
            return self.json_response({
                "status": "error",
                "message": "Invalid JSON",
            }, 400)

        if not isinstance(payload, dict):
            return self.json_response({
                "status": "error",
                "message": "Expected JSON object",
            }, 400)

        external_reference = payload.get("external_reference")
        received_quantities = payload.get("received_quantities")

        if (
            not isinstance(external_reference, str)
            or not external_reference.strip()
            or len(external_reference) > 128
        ):
            return self.json_response({
                "status": "error",
                "message": "Invalid external_reference",
            }, 400)

        external_reference = external_reference.strip()

        if (
            not isinstance(received_quantities, list)
            or not received_quantities
            or len(received_quantities) > 100
        ):
            return self.json_response({
                "status": "error",
                "message": "Invalid received_quantities",
            }, 400)

        quantities = {}
        lot_external_ids = {}

        for line in received_quantities:
            if not isinstance(line, dict):
                return self.json_response({
                    "status": "error",
                    "message": "Invalid received quantity line",
                }, 400)

            product_id = line.get("product_id")
            quantity = line.get("quantity")
            lot_external_id = line.get("lot_external_id")

            if (
                type(product_id) is not int
                or product_id <= 0
                or type(quantity) not in (int, float)
                or not math.isfinite(quantity)
                or quantity <= 0
                or quantity > 1000000000
                or product_id in quantities
            ):
                return self.json_response({
                    "status": "error",
                    "message": "Invalid or duplicate product quantity",
                }, 400)

            if lot_external_id is not None and (
                not isinstance(lot_external_id, str) or not lot_external_id.strip()
            ):
                return self.json_response({
                    "status": "error",
                    "message": "Invalid lot_external_id",
                }, 400)

            quantities[product_id] = quantity
            if lot_external_id:
                lot_external_ids[product_id] = lot_external_id.strip()

        try:
            env = request.env
            Picking = env["stock.picking"]
            Move = env["stock.move"]

            if (
                not Picking.has_access("read")
                or not Picking.has_access("write")
                or not Move.has_access("write")
            ):
                return self.json_response({
                    "status": "error",
                    "message": "Insufficient permissions",
                }, 403)

            # Lock the receipt to prevent simultaneous validation.
            env.cr.execute(
                """
                SELECT id
                FROM stock_picking
                WHERE id = %s
                FOR UPDATE NOWAIT
                """,
                (receipt_id,),
            )

            locked = env.cr.fetchone()

            if not locked:
                return self.json_response({
                    "status": "error",
                    "message": "Receipt not found",
                }, 404)

            # Refresh cached data after acquiring the lock.
            env.invalidate_all()

            receipt = Picking.search([
                ("id", "=", receipt_id),
                ("company_id", "in", env.companies.ids),
                ("picking_type_id.code", "=", "incoming"),
            ], limit=1)

            if not receipt:
                return self.json_response({
                    "status": "error",
                    "message": "Receipt not found",
                }, 404)

            if receipt.origin != external_reference:
                return self.json_response({
                    "status": "error",
                    "message": "External reference mismatch",
                }, 409)

            if receipt.state == "done":
                return self.json_response({
                    "status": "error",
                    "message": "Receipt already validated",
                    "receipt_id": receipt.id,
                }, 409)

            if receipt.state == "cancel":
                return self.json_response({
                    "status": "error",
                    "message": "Receipt is cancelled",
                }, 409)

            if receipt.state != "draft":
                return self.json_response({
                    "status": "error",
                    "message": "Only draft receipts can be validated",
                }, 409)

            # This API must not validate unrelated Odoo receipts. A
            # legacy receipt is recognized by its fixed prefix; a Phase G
            # WMS-first receipt (whose external_reference the WMS chose
            # itself, with no fixed prefix) is recognized instead by
            # having a real cool_agristock.wms.transaction row -- it could only
            # have gotten one by being created through this module's own
            # WMS-first creation path.
            is_legacy_cool_agristock_receipt = external_reference.startswith("COOL_AGRISTOCK-RCPT-")
            is_wms_first_receipt = bool(env["cool_agristock.wms.transaction"].sudo().search_count([
                ("transaction_type", "=", "receipt"),
                ("external_reference", "=", external_reference),
                ("picking_id", "=", receipt.id),
            ]))
            if not is_legacy_cool_agristock_receipt and not is_wms_first_receipt:
                return self.json_response({
                    "status": "error",
                    "message": "Receipt is not managed by Cool Agristock",
                }, 403)

            moves = receipt.move_ids.filtered(
                lambda m: m.state != "cancel"
            )

            if not moves:
                return self.json_response({
                    "status": "error",
                    "message": "Receipt has no active product lines",
                }, 400)

            # Phase 8 supports one move per product.
            move_products = [move.product_id.id for move in moves]

            if len(move_products) != len(set(move_products)):
                return self.json_response({
                    "status": "error",
                    "message": "Duplicate products in receipt are unsupported",
                }, 400)

            if set(move_products) != set(quantities):
                return self.json_response({
                    "status": "error",
                    "message": "Received products do not match receipt",
                }, 400)

            # Phase F: resolving a lot requires knowing which external
            # system this request is authorized for -- the same
            # resolution every lot/mapping-touching endpoint uses.
            # Legacy callers that never send lot_external_id never reach
            # this (resolve_authorized_external_system() is only called
            # when at least one line actually used the new field), so
            # an integration that doesn't use lots is entirely unaffected
            # even if its key happens to be unbound.
            external_system = None
            if lot_external_ids:
                try:
                    external_system = resolve_authorized_external_system()
                except ValidationError as exc:
                    return self.json_response(
                        {"status": "error", "message": str(exc)}, 403,
                    )
                if not external_system or external_system.company_id != receipt.company_id:
                    return self.json_response({
                        "status": "error",
                        "message": (
                            "This API key is not authorized for lot-tracked "
                            "receipts on this company."
                        ),
                    }, 403)

            Mapping = env["cool_agristock.external.id.mapping"]
            resolved_lots = {}

            for move in moves:
                product = move.product_id
                quantity = quantities[product.id]
                lot_external_id = lot_external_ids.get(product.id)

                if product.tracking != "none":
                    # Matches the original guard on dispatch validation:
                    # a tracked product can only be validated when the
                    # WMS names the exact lot/serial it was received
                    # under -- never silently aggregated or left unset.
                    if not lot_external_id:
                        return self.json_response({
                            "status": "error",
                            "message": "Lot or serial tracking is not supported yet",
                        }, 409)

                    lot_mapping = Mapping.resolve_mapping(
                        receipt.company_id, external_system, "stock.lot", lot_external_id,
                    )
                    if not lot_mapping:
                        return self.json_response({
                            "status": "error",
                            "message": "Lot not found: %s" % lot_external_id,
                        }, 404)
                    lot = env["stock.lot"].browse(lot_mapping.res_id)
                    if not lot.exists() or (
                        lot.company_id and lot.company_id != receipt.company_id
                    ):
                        return self.json_response({
                            "status": "error",
                            "message": "Lot not found: %s" % lot_external_id,
                        }, 404)
                    if lot.product_id != product:
                        return self.json_response({
                            "status": "error",
                            "message": (
                                "Lot %s does not belong to product %s" % (
                                    lot_external_id, product.display_name,
                                )
                            ),
                        }, 422)

                    if product.tracking == "serial" and not move.product_uom.is_zero(quantity - 1):
                        return self.json_response({
                            "status": "error",
                            "message": (
                                "Serial %s represents exactly one unit; "
                                "got a quantity of %s" % (lot_external_id, quantity)
                            ),
                        }, 422)

                    resolved_lots[product.id] = lot
                elif lot_external_id:
                    return self.json_response({
                        "status": "error",
                        "message": (
                            "Product %s is not lot/serial-tracked; "
                            "lot_external_id is not applicable" % product.display_name
                        ),
                    }, 422)

                # Initial implementation supports exact receipt quantities.
                # Partial receipts will be handled in a later phase.
                if not move.product_uom.is_zero(
                    quantity - move.product_uom_qty
                ):
                    return self.json_response({
                        "status": "error",
                        "message": "Received quantity must match expected quantity",
                    }, 400)

            # Confirm the draft and explicitly record received quantities.
            receipt.action_confirm()

            for move in moves:
                move.quantity = quantities[move.product_id.id]
                lot = resolved_lots.get(move.product_id.id)
                if lot:
                    # move.quantity's own inverse (_set_quantity ->
                    # _set_quantity_done) already created exactly one
                    # move line for this move (Phase 8's one-move-per-
                    # product invariant, and Step 5's exactly-one-unit
                    # rule for serials) -- this only assigns which lot
                    # it belongs to, using Odoo's own move_line_ids.lot_id
                    # field and its native _check_lot_product constraint.
                    move.move_line_ids.lot_id = lot.id

            result = receipt.button_validate()

            if receipt.state != "done":
                env.cr.rollback()
                return self.json_response({
                    "status": "error",
                    "message": "Receipt requires additional validation",
                }, 409)

            return self.json_response({
                "status": "success",
                "receipt_id": receipt.id,
                "receipt_reference": receipt.name,
                "external_reference": receipt.origin,
                "state": receipt.state,
            }, 200)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response({
                "status": "error",
                "message": "Access denied",
            }, 403)

        except (UserError, ValidationError) as exc:
            request.env.cr.rollback()
            _logger.warning(
                "Cool Agristock receipt validation rejected: %s", exc
            )
            return self.json_response({
                "status": "error",
                "message": "Odoo rejected receipt validation",
            }, 409)

        except Exception:
            request.env.cr.rollback()
            _logger.exception(
                "Cool Agristock receipt validation failed"
            )
            return self.json_response({
                "status": "error",
                "message": "Unable to validate receipt",
            }, 500)
