import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError
from .api_security import require_agriware_api_user, resolve_authorized_external_system

_logger = logging.getLogger(__name__)

# Explicit allow-list -- verified directly against this Odoo 19
# installation's res.partner field metadata (fields_get()) before use.
# This installation has no account/sale/purchase modules installed, so
# fields like property_account_payable_id, property_payment_term_id,
# or credit_limit don't even exist here -- but the allow-list approach
# protects against them regardless of what a real customer's Odoo
# instance has installed alongside this module, since nothing outside
# this list is ever read from the request body either way.
CREATE_ALLOWED_FIELDS = {"name", "email", "phone", "street", "city", "country_code"}
UPDATE_ALLOWED_FIELDS = {"name", "email", "phone", "street", "city", "country_code"}


class AgriwareSuppliersAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    def _authenticate(self):
        """Identical in spirit to AgriwareProductsAPI._authenticate() /
        AgriwareWarehousesAPI._authenticate() -- see controllers/products.py
        for the full reasoning behind resolve_authorized_external_system().
        """
        authorization = request.httprequest.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None, self.json_response(
                {"status": "error", "message": "Bearer token required"}, 401,
            )

        if not require_agriware_api_user():
            return None, self.json_response({
                "status": "error",
                "message": "Access denied: AgriWare API User role required",
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
                    "This API key is not authorized for supplier "
                    "synchronization: it is not bound to an active "
                    "external system."
                ),
            }, 403)

        return external_system, None

    def _resolve_country(self, country_code):
        """Resolve an ISO 3166-1 alpha-2 code to an existing res.country.
        Never creates one -- an unrecognized code is a client error, not
        something to guess at.
        """
        country = request.env["res.country"].sudo().search([
            ("code", "=", country_code.upper()),
        ], limit=1)
        return country

    @http.route(
        "/agriware/api/v1/suppliers",
        type="http",
        auth="bearer",
        methods=["GET"],
        csrf=False,
        readonly=True,
        save_session=False,
    )
    def get_suppliers(self, **kwargs):
        if not require_agriware_api_user():
            return self.json_response({
                "status": "error",
                "message": "Access denied: AgriWare API User role required",
            }, 403)

        try:
            partners = request.env["res.partner"].search([
                ("agriware_is_supplier", "=", True),
                ("company_id", "in", [False, *request.env.companies.ids]),
            ], limit=100, order="id")

            result = [{
                "id": partner.id,
                "name": partner.name,
                "email": partner.email or "",
                "phone": partner.phone or "",
                "country_code": partner.country_id.code or "",
            } for partner in partners]

            return self.json_response({
                "status": "success", "count": len(result), "suppliers": result,
            })

        except Exception:
            _logger.exception("AgriWare supplier retrieval failed")
            return self.json_response(
                {"status": "error", "message": "Unable to retrieve suppliers"}, 500,
            )

    @http.route(
        "/agriware/api/v1/suppliers",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def create_supplier(self, **kwargs):

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
        name = name.strip()

        for field in ("email", "phone", "street", "city", "country_code"):
            if field in payload and not isinstance(payload[field], str):
                return self.json_response(
                    {"status": "error", "message": "Invalid %s" % field}, 400,
                )

        country = None
        if payload.get("country_code"):
            country = self._resolve_country(payload["country_code"])
            if not country:
                return self.json_response({
                    "status": "error",
                    "message": "Unsupported country_code: %r" % (payload["country_code"],),
                }, 400)

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["agriware.external.id.mapping"]

            existing = Mapping.resolve_mapping(
                company, external_system, "res.partner", external_id,
            )
            if existing:
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "supplier_id": existing.res_id,
                }, 409)

            Partner = env["res.partner"].sudo()

            # Company-scoped, by design (Phase D, Step 5) -- unlike
            # products (shared, company_id=False), new WMS-created
            # suppliers are always scoped to the resolving company, so
            # a WMS integration can never create a record another
            # company's data could inadvertently depend on.
            partner = Partner.create({
                "name": name,
                "email": payload.get("email") or False,
                "phone": payload.get("phone") or False,
                "street": payload.get("street") or False,
                "city": payload.get("city") or False,
                "country_id": country.id if country else False,
                "company_id": company.id,
                "agriware_is_supplier": True,
            })

            mapping, created = Mapping.create_mapping(
                company, external_system, "res.partner", external_id, partner.id,
            )

            if not created:
                request.env.cr.rollback()
                return self.json_response({
                    "status": "error",
                    "message": "external_id already mapped",
                    "supplier_id": mapping.res_id,
                }, 409)

            return self.json_response({
                "status": "success",
                "supplier_id": partner.id,
                "external_id": external_id,
                "name": partner.name,
            }, 201)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("AgriWare supplier creation failed")
            return self.json_response(
                {"status": "error", "message": "Unable to create supplier"}, 500,
            )

    @http.route(
        "/agriware/api/v1/suppliers/<string:external_id>",
        type="http",
        auth="bearer",
        methods=["PATCH"],
        csrf=False,
        save_session=False,
    )
    def update_supplier(self, external_id, **kwargs):

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

        for field in ("name", "email", "phone", "street", "city", "country_code"):
            if field in payload and not isinstance(payload[field], str):
                return self.json_response(
                    {"status": "error", "message": "Invalid %s" % field}, 400,
                )

        if "name" in payload and not payload["name"].strip():
            return self.json_response(
                {"status": "error", "message": "name cannot be empty"}, 400,
            )

        country = None
        if payload.get("country_code"):
            country = self._resolve_country(payload["country_code"])
            if not country:
                return self.json_response({
                    "status": "error",
                    "message": "Unsupported country_code: %r" % (payload["country_code"],),
                }, 400)

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["agriware.external.id.mapping"]

            mapping = Mapping.resolve_mapping(
                company, external_system, "res.partner", external_id,
            )
            if not mapping:
                return self.json_response(
                    {"status": "error", "message": "No supplier mapped for this external_id"}, 404,
                )

            partner = env["res.partner"].sudo().browse(mapping.res_id)
            if not partner.exists():
                return self.json_response(
                    {"status": "error", "message": "No supplier mapped for this external_id"}, 404,
                )

            # Phase D, Step 5: a shared partner (company_id=False) can
            # affect every company in the database. Even though this
            # mapping is already scoped to one company (resolve_mapping
            # enforces that), a *shared* target record was never created
            # by this module -- create_supplier() always sets
            # company_id -- so one can only exist here via a manually
            # administered mapping. Refuse to touch it via the API
            # regardless, rather than silently writing to shared data.
            if not partner.company_id:
                return self.json_response({
                    "status": "error",
                    "message": (
                        "This supplier is a shared record (not scoped to "
                        "one company) and cannot be modified through this "
                        "API, since doing so could affect other companies."
                    ),
                }, 409)

            values = {}
            if "name" in payload:
                values["name"] = payload["name"].strip()
            if "email" in payload:
                values["email"] = payload["email"] or False
            if "phone" in payload:
                values["phone"] = payload["phone"] or False
            if "street" in payload:
                values["street"] = payload["street"] or False
            if "city" in payload:
                values["city"] = payload["city"] or False
            if "country_code" in payload:
                values["country_id"] = country.id if country else False

            values["agriware_is_supplier"] = True
            partner.write(values)

            return self.json_response({
                "status": "success",
                "supplier_id": partner.id,
                "external_id": external_id,
                "name": partner.name,
            }, 200)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response(
                {"status": "error", "message": "Access denied"}, 403,
            )

        except Exception:
            request.env.cr.rollback()
            _logger.exception("AgriWare supplier update failed")
            return self.json_response(
                {"status": "error", "message": "Unable to update supplier"}, 500,
            )
