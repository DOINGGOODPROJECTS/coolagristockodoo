import json
import logging
import math

from psycopg2 import errors

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare
from .api_security import require_cool_agristock_api_user, resolve_authorized_external_system

_logger = logging.getLogger(__name__)


class CoolAgristockDispatchValidationAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    @http.route(
        "/cool_agristock/api/v1/dispatches/<int:dispatch_id>/validate",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def validate_dispatch(self, dispatch_id, **kwargs):

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
        dispatched_quantities = payload.get("dispatched_quantities")

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
            not isinstance(dispatched_quantities, list)
            or not dispatched_quantities
            or len(dispatched_quantities) > 100
        ):
            return self.json_response({
                "status": "error",
                "message": "Invalid dispatched_quantities",
            }, 400)

        quantities = {}
        lot_external_ids = {}

        for line in dispatched_quantities:

            if not isinstance(line, dict):
                return self.json_response({
                    "status": "error",
                    "message": "Invalid dispatch line",
                }, 400)

            product_id = line.get("product_id")
            quantity = line.get("quantity")
            lot_external_id = line.get("lot_external_id")

            if (
                type(product_id) is not int
                or product_id <= 0
                or type(quantity) not in (int, float)
                or not math.isfinite(quantity)
                or not (0 < quantity <= 1000000000)
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

        env = request.env

        def error_response(message, status):
            env.cr.rollback()
            return self.json_response({
                "status": "error",
                "message": message,
            }, status)

        try:
            Picking = env["stock.picking"]
            Move = env["stock.move"]

            if not (
                Picking.has_access("read")
                and Picking.has_access("write")
                and Move.has_access("read")
                and Move.has_access("write")
            ):
                return error_response(
                    "Insufficient permissions", 403
                )

            # Prevent simultaneous validation of this dispatch.
            try:
                with env.cr.savepoint():
                    env.cr.execute(
                        """
                        SELECT id
                        FROM stock_picking
                        WHERE id = %s
                        FOR UPDATE NOWAIT
                        """,
                        (dispatch_id,),
                    )
                    locked = env.cr.fetchone()

            except errors.LockNotAvailable:
                return error_response(
                    "Dispatch is being processed", 409
                )

            if not locked:
                return error_response(
                    "Dispatch not found", 404
                )

            env.invalidate_all()

            dispatch = Picking.search([
                ("id", "=", dispatch_id),
                ("company_id", "in", env.companies.ids),
                ("picking_type_id.code", "=", "outgoing"),
            ], limit=1)

            if not dispatch:
                return error_response(
                    "Outgoing dispatch not found", 404
                )

            if dispatch.origin != external_reference:
                return error_response(
                    "External reference mismatch", 409
                )

            if dispatch.state == "done":
                return error_response(
                    "Dispatch already validated", 409
                )

            if dispatch.state == "cancel":
                return error_response(
                    "Dispatch is cancelled", 409
                )

            if dispatch.state != "draft":
                return error_response(
                    "Only draft dispatches are supported", 409
                )

            # This API must not validate unrelated Odoo deliveries. See
            # receipt_validation.py's identical guard for the full
            # reasoning (legacy fixed prefix, or a real Phase G
            # cool_agristock.wms.transaction row).
            is_legacy_cool_agristock_dispatch = external_reference.startswith("COOL_AGRISTOCK-DISP-")
            is_wms_first_dispatch = bool(env["cool_agristock.wms.transaction"].sudo().search_count([
                ("transaction_type", "=", "dispatch"),
                ("external_reference", "=", external_reference),
                ("picking_id", "=", dispatch.id),
            ]))
            if not is_legacy_cool_agristock_dispatch and not is_wms_first_dispatch:
                return error_response(
                    "Dispatch is not managed by Cool Agristock", 403
                )

            moves = dispatch.move_ids.filtered(
                lambda move: move.state != "cancel"
            )

            if not moves:
                return error_response(
                    "Dispatch contains no active movements", 409
                )

            if len(moves) != len(quantities):
                return error_response(
                    "Dispatched products do not match order", 409
                )

            # Phase F: resolving a lot requires knowing which external
            # system this request is authorized for. Only resolved when
            # at least one line actually used lot_external_id, so a
            # legacy caller that never sends it is entirely unaffected
            # even if its key happens to be unbound.
            external_system = None
            if lot_external_ids:
                try:
                    external_system = resolve_authorized_external_system()
                except ValidationError as exc:
                    return error_response(str(exc), 403)
                if not external_system or external_system.company_id != dispatch.company_id:
                    return error_response(
                        "This API key is not authorized for lot-tracked "
                        "dispatches on this company.", 403,
                    )

            Mapping = env["cool_agristock.external.id.mapping"]
            resolved_lots = {}

            for move in moves:

                product = move.product_id

                if product.id not in quantities:
                    return error_response(
                        "Product mismatch", 409
                    )

                lot_external_id = lot_external_ids.get(product.id)

                if product.tracking != "none":
                    if not lot_external_id:
                        return error_response(
                            "Lot or serial tracking is not supported yet",
                            409,
                        )

                    lot_mapping = Mapping.resolve_mapping(
                        dispatch.company_id, external_system, "stock.lot", lot_external_id,
                    )
                    if not lot_mapping:
                        return error_response(
                            "Lot not found: %s" % lot_external_id, 404,
                        )
                    lot = env["stock.lot"].browse(lot_mapping.res_id)
                    if not lot.exists() or (
                        lot.company_id and lot.company_id != dispatch.company_id
                    ):
                        return error_response(
                            "Lot not found: %s" % lot_external_id, 404,
                        )
                    if lot.product_id != product:
                        return error_response(
                            "Lot %s does not belong to product %s" % (
                                lot_external_id, product.display_name,
                            ), 422,
                        )

                    if product.tracking == "serial" and not move.product_uom.is_zero(
                        quantities[product.id] - 1
                    ):
                        return error_response(
                            "Serial %s represents exactly one unit; got a "
                            "quantity of %s" % (lot_external_id, quantities[product.id]), 422,
                        )

                    resolved_lots[product.id] = lot
                elif lot_external_id:
                    return error_response(
                        "Product %s is not lot/serial-tracked; "
                        "lot_external_id is not applicable" % product.display_name, 422,
                    )

                expected = move.product_uom_qty
                received = quantities[product.id]

                if float_compare(
                    expected,
                    received,
                    precision_rounding=move.product_uom.rounding,
                ) != 0:
                    return error_response(
                        "Partial dispatches are not supported", 409
                    )

            # Confirm through Odoo's standard workflow.
            dispatch.action_confirm()
            env.invalidate_all()

            moves = dispatch.move_ids.filtered(
                lambda move: move.state != "cancel"
            )

            # Phase F: pin tracked moves to the exact requested lot
            # *before* the generic reservation pass below -- Odoo's own
            # native _update_reserved_quantity(), which only reserves
            # from the named lot and reports back how much it actually
            # found, so a lot with insufficient stock is caught here
            # rather than silently falling back to a different lot.
            #
            # action_confirm() above can itself auto-reserve already
            # (confirmed directly: with only one lot in stock, Odoo
            # reserves it immediately on confirm, before this code ever
            # runs) -- _update_reserved_quantity()'s `need` is additive
            # on top of whatever is already reserved, not an absolute
            # target, so reusing it naively here would double-reserve.
            # Clearing any existing reservation on the move first makes
            # the outcome deterministic regardless of what Odoo's own
            # confirm-time reservation already did.
            for move in moves:
                lot = resolved_lots.get(move.product_id.id)
                if not lot:
                    continue
                move.move_line_ids.unlink()
                needed = quantities[move.product_id.id]
                taken = move._update_reserved_quantity(
                    needed, move.location_id, lot_id=lot, strict=True,
                )
                if float_compare(taken, needed, precision_rounding=move.product_uom.rounding) != 0:
                    return error_response(
                        "Insufficient stock for lot %s" % lot.name, 409,
                    )

            # _update_reserved_quantity() above wrote move_line_ids
            # directly; move.quantity (a stored field computed from
            # move_line_ids.quantity) must be refreshed before
            # _action_assign() reads it, or it would still see the
            # pre-reservation value and reserve the same need a second
            # time on top of the lot-pinned reservation already done.
            env.invalidate_all()

            # Already-fully-reserved (tracked) moves are recognized as
            # such and left untouched; every other move is reserved
            # exactly as before this phase.
            moves._action_assign()

            env.invalidate_all()

            moves = dispatch.move_ids.filtered(
                lambda move: move.state != "cancel"
            )

            # A dispatch must be fully reserved before validation.
            for move in moves:

                reserved = sum(
                    move.move_line_ids.mapped("quantity")
                )

                if float_compare(
                    reserved,
                    move.product_uom_qty,
                    precision_rounding=move.product_uom.rounding,
                ) < 0:
                    return error_response(
                        "Insufficient reserved stock", 409
                    )

            for move in moves:
                move.picked = True

            result = dispatch.button_validate()

            env.invalidate_all()

            if dispatch.state != "done":
                return error_response(
                    "Odoo did not complete the dispatch", 409
                )

            return self.json_response({
                "status": "success",
                "dispatch_id": dispatch.id,
                "dispatch_reference": dispatch.name,
                "external_reference": dispatch.origin,
                "state": dispatch.state,
            }, 200)

        except AccessError:
            return error_response("Access denied", 403)

        except (UserError, ValidationError) as exc:
            _logger.warning(
                "Cool Agristock dispatch validation rejected: %s",
                exc,
            )
            return error_response(
                "Odoo rejected dispatch validation", 409
            )

        except Exception:
            env.cr.rollback()
            _logger.exception(
                "Cool Agristock dispatch validation failed"
            )
            return self.json_response({
                "status": "error",
                "message": "Unable to validate dispatch",
            }, 500)
