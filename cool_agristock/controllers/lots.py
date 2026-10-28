import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError
from .api_security import require_cool_agristock_api_user, resolve_authorized_external_system

_logger = logging.getLogger(__name__)

# Explicit allow-list -- verified directly against this Odoo 19
# installation's stock.lot field metadata before use. "name" is the
# lot/serial number identity itself; "ref" and "note" are the only two
# genuinely free-form, non-structural metadata fields stock.lot exposes
# (internal reference, free-text description). Everything else on the
# model -- company_id, product_id, location_id, quant_ids, lot_properties
# -- is either resolved server-side or deliberately not exposed (see
# docs/LOT_BATCH_SYNCHRONIZATION.md's Supported lot fields section).
CREATE_ALLOWED_FIELDS = {"name", "ref", "note"}
UPDATE_ALLOWED_FIELDS = {"name", "ref", "note"}


class CoolAgristockLotsAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    def _authenticate(self):
        """Identical in spirit to every other Phase B/C/D/E endpoint's
        _authenticate() -- see controllers/products.py for the full
        reasoning behind resolve_authorized_external_system().
        """
        authorization = request.httprequest.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None, self.json_response(
                {"status": "error", "message": "Bearer token required"}, 401,
            )

        if not require_cool_agristock_api_user():
            return None, self.json_response({
                "status": "error",
                "message": "Access denied: Cool Agristock API User role required",
            }, 403)

        try:
            external_system = resolve_authorized_external_system()
        except ValidationError as exc:
            return None, self.json_response(
                {"status": "error", "message": str(exc)}, 403,
            )

        if not external_system:
            return None, self.json_response({
                "status": "error",
                "message": (
                    "This API key is not authorized for lot synchronization: "
                    "it is not bound to an active external system."
                ),
            }, 403)

        return external_system, None

    @http.route(
        "/cool_agristock/api/v1/lots",
        type="http",
        auth="bearer",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def get_lots(self, **kwargs):
        if not require_cool_agristock_api_user():
            return self.json_response({
                "status": "error",
                "message": "Access denied: Cool Agristock API User role required",
            }, 403)

        try:
            lots = request.env["stock.lot"].search([
                ("company_id", "in", [False, *request.env.companies.ids]),
            ], limit=100, order="id")

            result = [{
                "id": lot.id,
                "name": lot.name,
                "product_id": lot.product_id.id,
                "ref": lot.ref or "",
            } for lot in lots]

            return self.json_response({
                "status": "success", "count": len(result), "lots": result,
            })

        except Exception:
            _logger.exception("Cool Agristock lot retrieval failed")
            return self.json_response(
                {"status": "error", "message": "Unable to retrieve lots"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/lots",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def create_lot(self, **kwargs):

        external_system, error = self._authenticate()
        if error:
            return error

        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except (ValueError, UnicodeDecodeError):
            return self.json_response(
                {"status": "error", "message": "Invalid JSON"}, 400,
            )

        if not isinstance(payload, dict):
            return self.json_response(
                {"status": "error", "message": "Expected JSON object"}, 400,
            )

        unknown_fields = set(payload.keys()) - CREATE_ALLOWED_FIELDS - {
            "external_id", "product_external_id",
        }
        if unknown_fields:
            return self.json_response({
                "status": "error",
                "message": "Unsupported field(s): %s" % ", ".join(sorted(unknown_fields)),
            }, 400)

        external_id = payload.get("external_id")
        product_external_id = payload.get("product_external_id")
        name = payload.get("name")

        if (
            not isinstance(external_id, str)
            or not external_id.strip()
            or len(external_id) > 128
        ):
            return self.json_response(
                {"status": "error", "message": "Invalid external_id"}, 400,
            )
        external_id = external_id.strip()

        if not isinstance(product_external_id, str) or not product_external_id.strip():
            return self.json_response(
                {"status": "error", "message": "Invalid product_external_id"}, 400,
            )
        product_external_id = product_external_id.strip()

        if not isinstance(name, str) or not name.strip():
            return self.json_response(
                {"status": "error", "message": "Invalid or missing name"}, 400,
            )
        name = name.strip()

        for field in ("ref", "note"):
            if field in payload and not isinstance(payload[field], str):
                return self.json_response(
                    {"status": "error", "message": "Invalid %s" % field}, 400,
                )

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["cool_agristock.external.id.mapping"]

            # Check for an existing mapping *before* creating anything --
            # same precedent as every other Phase B-E endpoint. A lot's
            # identity (name/product) is never silently remapped onto a
            # later, different submission under the same external_id.
            existing = Mapping.resolve_mapping(
                company, external_system, "stock.lot", external_id,
            )
            if existing:
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "lot_id": existing.res_id,
                }, 409)

            product_mapping = Mapping.resolve_mapping(
                company, external_system, "product.product", product_external_id,
            )
            if not product_mapping:
                return self.json_response(
                    {"status": "error", "message": "Product not found"}, 404,
                )
            product = env["product.product"].browse(product_mapping.res_id)
            if not product.exists() or (
                product.company_id and product.company_id != company
            ):
                return self.json_response(
                    {"status": "error", "message": "Product not found"}, 404,
                )

            if product.tracking == "none":
                return self.json_response({
                    "status": "error",
                    "message": (
                        "Product %s is not configured for lot or serial "
                        "tracking -- it cannot have a lot/serial number "
                        "assigned." % product_external_id
                    ),
                }, 422)

            # Lot.create() natively enforces _check_lot_product (lot
            # belongs to exactly this product) and _check_unique_lot
            # (no duplicate name for this product/company) -- Odoo's own
            # constraints, not reimplemented here.
            Lot = env["stock.lot"]
            if not Lot.has_access("create"):
                return self.json_response(
                    {"status": "error", "message": "Insufficient permissions"}, 403,
                )

            try:
                with env.cr.savepoint():
                    lot = Lot.create({
                        "name": name,
                        "product_id": product.id,
                        "company_id": company.id,
                        "ref": payload.get("ref") or False,
                        "note": payload.get("note") or False,
                    })
            except ValidationError:
                # Odoo's own _check_unique_lot fired -- this exact
                # product/name/company combination already has a lot,
                # just not one mapped to this external_id.
                return self.json_response({
                    "status": "error",
                    "message": (
                        "A lot named %r already exists for this product" % name
                    ),
                }, 409)

            mapping, created = Mapping.create_mapping(
                company, external_system, "stock.lot", external_id, lot.id,
            )

            if not created:
                request.env.cr.rollback()
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "lot_id": mapping.res_id,
                }, 409)

            return self.json_response({
                "status": "success",
                "lot_id": lot.id,
                "external_id": external_id,
                "name": lot.name,
                "product_external_id": product_external_id,
            }, 201)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock lot creation failed")
            return self.json_response(
                {"status": "error", "message": "Unable to create lot"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/lots/<string:external_id>",
        type="http",
        auth="bearer",
        methods=["PATCH"],
        csrf=False,
        save_session=False,
    )
    def update_lot(self, external_id, **kwargs):

        external_system, error = self._authenticate()
        if error:
            return error

        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except (ValueError, UnicodeDecodeError):
            return self.json_response(
                {"status": "error", "message": "Invalid JSON"}, 400,
            )

        if not isinstance(payload, dict):
            return self.json_response(
                {"status": "error", "message": "Expected JSON object"}, 400,
            )

        unknown_fields = set(payload.keys()) - UPDATE_ALLOWED_FIELDS
        if unknown_fields:
            return self.json_response({
                "status": "error",
                "message": "Unsupported field(s): %s" % ", ".join(sorted(unknown_fields)),
            }, 400)

        if not payload:
            return self.json_response(
                {"status": "error", "message": "No fields to update"}, 400,
            )

        for field in ("name", "ref", "note"):
            if field in payload and not isinstance(payload[field], str):
                return self.json_response(
                    {"status": "error", "message": "Invalid %s" % field}, 400,
                )

        if "name" in payload and not payload["name"].strip():
            return self.json_response(
                {"status": "error", "message": "name cannot be empty"}, 400,
            )

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["cool_agristock.external.id.mapping"]

            mapping = Mapping.resolve_mapping(
                company, external_system, "stock.lot", external_id,
            )
            if not mapping:
                return self.json_response(
                    {"status": "error", "message": "No lot mapped for this external_id"}, 404,
                )

            Lot = env["stock.lot"]
            lot = Lot.browse(mapping.res_id)
            if not lot.exists():
                return self.json_response(
                    {"status": "error", "message": "No lot mapped for this external_id"}, 404,
                )

            if "name" in payload:
                # Phase F, Step 6: a lot identifier cannot be changed
                # once it has participated in any stock movement --
                # confirmed live against stock_move_line.lot_id, not
                # assumed. Renaming it afterward would desynchronize the
                # already-recorded traceability history from the lot's
                # displayed name.
                has_history = env["stock.move.line"].search_count([
                    ("lot_id", "=", lot.id),
                ]) > 0
                if has_history:
                    return self.json_response({
                        "status": "error",
                        "message": (
                            "This lot already has recorded stock movements -- "
                            "its name cannot be changed without risking "
                            "traceability data corruption"
                        ),
                    }, 409)

            values = {}
            if "name" in payload:
                values["name"] = payload["name"].strip()
            if "ref" in payload:
                values["ref"] = payload["ref"] or False
            if "note" in payload:
                values["note"] = payload["note"] or False

            try:
                with env.cr.savepoint():
                    lot.write(values)
            except ValidationError:
                return self.json_response({
                    "status": "error",
                    "message": (
                        "A lot named %r already exists for this product" % values.get("name")
                    ),
                }, 409)

            return self.json_response({
                "status": "success",
                "lot_id": lot.id,
                "external_id": external_id,
                "name": lot.name,
            }, 200)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock lot update failed")
            return self.json_response(
                {"status": "error", "message": "Unable to update lot"}, 500,
            )
