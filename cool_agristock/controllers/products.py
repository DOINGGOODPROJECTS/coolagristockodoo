import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError
from .api_security import require_cool_agristock_api_user, resolve_authorized_external_system

_logger = logging.getLogger(__name__)

# Explicit allow-list -- WMS-owned fields only. Verified directly against
# this Odoo 19 installation's product.product field metadata before use
# (fields_get()), not assumed. Everything NOT on this list (sales price,
# cost, taxes, accounting properties, valuation configuration, and every
# other ERP-specific setting) is never settable through these endpoints,
# by construction -- there is no block-list to accidentally miss a field
# on.
CREATE_ALLOWED_FIELDS = {"name", "default_code", "barcode", "description", "unit"}

# PATCH deliberately excludes "unit": changing a product's unit of
# measure after creation is unsafe once stock or transactions reference
# it (see docs/PRODUCT_SYNCHRONIZATION.md's Known limitations) -- not
# implemented safely yet, so not exposed at all rather than exposed
# without the safety check it would need.
UPDATE_ALLOWED_FIELDS = {"name", "default_code", "barcode", "description"}

# Small, explicit, hardcoded set of unambiguous units -- verified to
# exist in this installed Odoo 19 by checking env.ref() directly, not
# guessed. Full database-backed UOM mapping (admin-extensible) remains
# scheduled for Phase D; this is intentionally not that.
SUPPORTED_UNITS = {
    "kg": "uom.product_uom_kgm",
    "g": "uom.product_uom_gram",
    "ton": "uom.product_uom_ton",
    "t": "uom.product_uom_ton",
    "l": "uom.product_uom_litre",
    "liter": "uom.product_uom_litre",
    "litre": "uom.product_uom_litre",
    "unit": "uom.product_uom_unit",
    "units": "uom.product_uom_unit",
    "pcs": "uom.product_uom_unit",
}

DEFAULT_UNIT_XMLID = "uom.product_uom_unit"


class CoolAgristockProductsAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    def _authenticate(self):
        """Shared auth + authorization-resolution for both endpoints.

        :returns: (external_system, error_response). Exactly one of the
            two is set -- check error_response first.
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
                    "This API key is not authorized for product "
                    "synchronization: it is not bound to an active "
                    "external system."
                ),
            }, 403)

        return external_system, None

    @http.route(
        "/cool_agristock/api/v1/products",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def create_product(self, **kwargs):

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

        for field in ("default_code", "barcode", "description"):
            if field in payload and not isinstance(payload[field], str):
                return self.json_response(
                    {"status": "error", "message": "Invalid %s" % field}, 400,
                )

        unit_code = payload.get("unit")
        if unit_code is not None and not isinstance(unit_code, str):
            return self.json_response(
                {"status": "error", "message": "Invalid unit"}, 400,
            )

        try:
            env = request.env
            company = external_system.company_id

            Product = env["product.product"]
            if not Product.has_access("create"):
                return self.json_response(
                    {"status": "error", "message": "Insufficient permissions"}, 403,
                )

            Mapping = env["cool_agristock.external.id.mapping"]

            # Check for an existing mapping *before* creating anything --
            # the common-case duplicate must never create an orphaned
            # product. See docs/PRODUCT_SYNCHRONIZATION.md's Duplicate
            # handling section for the full reasoning.
            existing = Mapping.resolve_mapping(
                company, external_system, "product.product", external_id,
            )
            if existing:
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "product_id": existing.res_id,
                }, 409)

            # Resolve the unit: an admin-configured cool_agristock.uom.mapping
            # row takes precedence (Phase D), falling back to the small
            # hardcoded set from Phase B for full backward compatibility
            # -- an integration that has never configured a mapping, and
            # only ever sends "kg"/"unit"/etc., is entirely unaffected.
            if unit_code is not None:
                UomMapping = env["cool_agristock.uom.mapping"]
                uom = UomMapping.resolve_unit(company, external_system, unit_code)
                if not uom:
                    if unit_code.lower() not in SUPPORTED_UNITS:
                        return self.json_response({
                            "status": "error",
                            "message": "Unsupported unit: %r" % (unit_code,),
                        }, 400)
                    uom = env.ref(SUPPORTED_UNITS[unit_code.lower()])
            else:
                uom = env.ref(DEFAULT_UNIT_XMLID)

            product = Product.create({
                "name": name.strip(),
                "default_code": payload.get("default_code") or False,
                "barcode": payload.get("barcode") or False,
                "description": payload.get("description") or False,
                "uom_id": uom.id,
                "type": "consu",
                "is_storable": True,
                "tracking": "none",
                "company_id": False,
            })

            mapping, created = Mapping.create_mapping(
                external_system.company_id, external_system,
                "product.product", external_id, product.id,
            )

            if not created:
                # Lost a race against a concurrent request for the same
                # external_id *after* we already created a product row.
                # Roll back everything -- including the product we just
                # created -- rather than leaving it orphaned. Odoo
                # auto-commits a successful http-type response; this
                # explicit rollback is what makes the 409 path actually
                # discard the product instead of silently persisting it.
                request.env.cr.rollback()
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "product_id": mapping.res_id,
                }, 409)

            return self.json_response({
                "status": "success",
                "product_id": product.id,
                "external_id": external_id,
                "name": product.name,
            }, 201)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock product creation failed")
            return self.json_response(
                {"status": "error", "message": "Unable to create product"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/products/<string:external_id>",
        type="http",
        auth="bearer",
        methods=["PATCH"],
        csrf=False,
        save_session=False,
    )
    def update_product(self, external_id, **kwargs):

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

        for field in ("name", "default_code", "barcode", "description"):
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
            Mapping = env["cool_agristock.external.id.mapping"]

            mapping = Mapping.resolve_mapping(
                external_system.company_id, external_system,
                "product.product", external_id,
            )
            if not mapping:
                return self.json_response(
                    {"status": "error", "message": "No product mapped for this external_id"}, 404,
                )

            Product = env["product.product"]
            if not Product.has_access("write"):
                return self.json_response(
                    {"status": "error", "message": "Insufficient permissions"}, 403,
                )

            product = Product.browse(mapping.res_id)
            if not product.exists():
                return self.json_response(
                    {"status": "error", "message": "No product mapped for this external_id"}, 404,
                )

            values = {}
            if "name" in payload:
                values["name"] = payload["name"].strip()
            if "default_code" in payload:
                values["default_code"] = payload["default_code"] or False
            if "barcode" in payload:
                values["barcode"] = payload["barcode"] or False
            if "description" in payload:
                values["description"] = payload["description"] or False

            product.write(values)

            return self.json_response({
                "status": "success",
                "product_id": product.id,
                "external_id": external_id,
                "name": product.name,
            }, 200)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock product update failed")
            return self.json_response(
                {"status": "error", "message": "Unable to update product"}, 500,
            )
