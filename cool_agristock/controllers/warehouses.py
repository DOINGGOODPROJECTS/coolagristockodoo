import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError
from .api_security import require_cool_agristock_api_user, resolve_authorized_external_system

_logger = logging.getLogger(__name__)

# Explicit allow-list -- verified directly against this Odoo 19
# installation's stock.warehouse field metadata (name, code, company_id,
# view_location_id, lot_stock_id, route_ids, reception_steps,
# delivery_steps, pick_type_id/in_type_id/out_type_id/..., mto_pull_id,
# resupply_*) before use, not assumed. Every routing/picking-type/
# resupply/location field is deliberately excluded -- Odoo's own
# stock.warehouse.create() generates all of that internally; exposing
# any of it to an API client would mean letting a WMS reconfigure
# operational routing, which Phase 7 explicitly forbids.
CREATE_ALLOWED_FIELDS = {"name", "code"}

# PATCH excludes "code" entirely, on purpose. A warehouse's code is used
# only once, at creation time, to name its auto-generated sequences and
# locations (see stock.warehouse.create()) -- nothing re-propagates a
# later code change into those already-named records, so changing it
# afterward would desynchronize the warehouse's displayed code from
# its real internal naming. Per the task's own instruction ("reject the
# change rather than risk data corruption"), it is simply not exposed.
UPDATE_ALLOWED_FIELDS = {"name"}

MAX_CODE_LENGTH = 5  # stock.warehouse.code is a Char(size=5) in Odoo core.


class CoolAgristockWarehousesAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    def _authenticate(self):
        """Shared auth + authorization-resolution, identical in spirit to
        CoolAgristockProductsAPI._authenticate() -- see controllers/products.py
        for the full reasoning behind resolve_authorized_external_system().
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
                    "This API key is not authorized for warehouse "
                    "synchronization: it is not bound to an active "
                    "external system."
                ),
            }, 403)

        return external_system, None

    @http.route(
        "/cool_agristock/api/v1/warehouses",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def create_warehouse(self, **kwargs):

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

        unknown_fields = set(payload.keys()) - CREATE_ALLOWED_FIELDS - {"external_id"}
        if unknown_fields:
            return self.json_response({
                "status": "error",
                "message": "Unsupported field(s): %s" % ", ".join(sorted(unknown_fields)),
            }, 400)

        external_id = payload.get("external_id")
        name = payload.get("name")
        code = payload.get("code")

        if (
            not isinstance(external_id, str)
            or not external_id.strip()
            or len(external_id) > 128
        ):
            return self.json_response(
                {"status": "error", "message": "Invalid external_id"}, 400,
            )
        external_id = external_id.strip()

        if not isinstance(name, str) or not name.strip():
            return self.json_response(
                {"status": "error", "message": "Invalid or missing name"}, 400,
            )
        name = name.strip()

        if not isinstance(code, str) or not code.strip():
            return self.json_response(
                {"status": "error", "message": "Invalid or missing code"}, 400,
            )
        code = code.strip()

        if len(code) > MAX_CODE_LENGTH:
            return self.json_response({
                "status": "error",
                "message": (
                    "Unsupported warehouse configuration: code must be "
                    "%d characters or fewer" % MAX_CODE_LENGTH
                ),
            }, 422)

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["cool_agristock.external.id.mapping"]

            # Check for an existing mapping *before* creating anything.
            existing = Mapping.resolve_mapping(
                company, external_system, "stock.warehouse", external_id,
            )
            if existing:
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "warehouse_id": existing.res_id,
                }, 409)

            Warehouse = env["stock.warehouse"].sudo()

            # Pre-check both of stock.warehouse's own uniqueness
            # constraints (name AND code are each unique per company) so
            # a conflict surfaces as a clean 409, not a raw DB error.
            if Warehouse.search_count([
                ("name", "=", name), ("company_id", "=", company.id),
            ]):
                return self.json_response(
                    {"status": "error", "message": "Warehouse name already in use"}, 409,
                )
            if Warehouse.search_count([
                ("code", "=", code), ("company_id", "=", company.id),
            ]):
                return self.json_response(
                    {"status": "error", "message": "Warehouse code already in use"}, 409,
                )

            # sudo(): deliberately bypasses ir.model.access for
            # stock.warehouse/stock.location/stock.picking.type/
            # stock.route/stock.rule/ir.sequence, all of which
            # stock.warehouse.create() touches internally to build the
            # operational structure Phase 7 requires a WMS never control
            # directly. This is gated by the explicit auth + resolved-
            # external-system check above, not exposed as a general
            # capability -- see docs/WAREHOUSE_SYNCHRONIZATION.md's
            # Security section for the full reasoning.
            warehouse = Warehouse.create({
                "name": name,
                "code": code,
                "company_id": company.id,
            })

            mapping, created = Mapping.create_mapping(
                company, external_system, "stock.warehouse", external_id, warehouse.id,
            )

            if not created:
                # Lost a race against a concurrent request for the same
                # external_id after the warehouse (and its auto-created
                # locations/picking types/routes) already exist. Roll
                # back everything rather than leaving any of it behind.
                request.env.cr.rollback()
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "warehouse_id": mapping.res_id,
                }, 409)

            return self.json_response({
                "status": "success",
                "warehouse_id": warehouse.id,
                "external_id": external_id,
                "name": warehouse.name,
                "code": warehouse.code,
            }, 201)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock warehouse creation failed")
            return self.json_response(
                {"status": "error", "message": "Unable to create warehouse"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/warehouses/<string:external_id>",
        type="http",
        auth="bearer",
        methods=["PATCH"],
        csrf=False,
        save_session=False,
    )
    def update_warehouse(self, external_id, **kwargs):

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

        if "code" in payload:
            return self.json_response({
                "status": "error",
                "message": (
                    "code cannot be changed once a warehouse is created "
                    "(its locations and sequences are already named from "
                    "it) -- create a new warehouse instead if the code "
                    "must change"
                ),
            }, 400)

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

        name = payload.get("name")
        if "name" in payload and (not isinstance(name, str) or not name.strip()):
            return self.json_response(
                {"status": "error", "message": "Invalid name"}, 400,
            )

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["cool_agristock.external.id.mapping"]

            mapping = Mapping.resolve_mapping(
                company, external_system, "stock.warehouse", external_id,
            )
            if not mapping:
                return self.json_response(
                    {"status": "error", "message": "No warehouse mapped for this external_id"}, 404,
                )

            Warehouse = env["stock.warehouse"].sudo()
            warehouse = Warehouse.browse(mapping.res_id)
            if not warehouse.exists():
                return self.json_response(
                    {"status": "error", "message": "No warehouse mapped for this external_id"}, 404,
                )

            if "name" in payload:
                name = name.strip()
                if Warehouse.search_count([
                    ("name", "=", name), ("company_id", "=", company.id),
                    ("id", "!=", warehouse.id),
                ]):
                    return self.json_response(
                        {"status": "error", "message": "Warehouse name already in use"}, 409,
                    )
                warehouse.write({"name": name})

            return self.json_response({
                "status": "success",
                "warehouse_id": warehouse.id,
                "external_id": external_id,
                "name": warehouse.name,
                "code": warehouse.code,
            }, 200)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock warehouse update failed")
            return self.json_response(
                {"status": "error", "message": "Unable to update warehouse"}, 500,
            )
