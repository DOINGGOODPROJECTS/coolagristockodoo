import json
import logging

from odoo import http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import Response, request

from .api_security import (
    require_cool_agristock_api_user,
    resolve_authorized_external_system,
)

_logger = logging.getLogger(__name__)
CREATE_ALLOWED_FIELDS = {"name", "barcode"}
UPDATE_ALLOWED_FIELDS = {"name"}


class CoolAgristockLocationsAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(json.dumps(data), status=status, content_type="application/json")

    def _authenticate(self, write=False):
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
        if not write:
            return False, None
        try:
            system = resolve_authorized_external_system()
        except ValidationError as exc:
            return None, self.json_response({"status": "error", "message": str(exc)}, 403)
        if not system:
            return None, self.json_response({
                "status": "error",
                "message": "API key is not bound to an active external system",
            }, 403)
        return system, None

    @http.route(
        "/cool_agristock/api/v1/locations",
        type="http", auth="bearer", methods=["GET"],
        csrf=False, readonly=True, save_session=False,
    )
    def get_locations(self, **kwargs):
        _, error = self._authenticate()
        if error:
            return error
        try:
            try:
                system = resolve_authorized_external_system()
            except ValidationError as exc:
                return self.json_response(
                    {"status": "error", "message": str(exc)}, 403,
                )
            locations = request.env["stock.location"].search([
                ("usage", "=", "internal"),
                ("company_id", "in", [False, *request.env.companies.ids]),
            ], limit=100, order="id")
            mappings = request.env["cool_agristock.external.id.mapping"].sudo().search(
                [
                    ("company_id", "=", system.company_id.id),
                    ("external_system_id", "=", system.id),
                    ("res_model", "=", "stock.location"),
                    ("res_id", "in", locations.ids),
                ] if system else [("id", "=", 0)]
            )
            external_ids = {mapping.res_id: mapping.external_id for mapping in mappings}
            result = [{
                "id": location.id,
                "external_id": external_ids.get(location.id),
                "name": location.name,
                "complete_name": location.complete_name,
                "barcode": location.barcode or "",
                "parent_location_id": location.location_id.id,
                "company_id": location.company_id.id or None,
            } for location in locations]
            return self.json_response({
                "status": "success", "count": len(result), "locations": result,
            })
        except Exception:
            _logger.exception("Cool Agristock location retrieval failed")
            return self.json_response(
                {"status": "error", "message": "Unable to retrieve locations"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/locations",
        type="http", auth="bearer", methods=["POST"],
        csrf=False, save_session=False,
    )
    def create_location(self, **kwargs):
        system, error = self._authenticate(write=True)
        if error:
            return error
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except (ValueError, UnicodeDecodeError):
            return self.json_response({"status": "error", "message": "Invalid JSON"}, 400)
        if not isinstance(payload, dict):
            return self.json_response({"status": "error", "message": "Expected JSON object"}, 400)
        unknown = set(payload) - CREATE_ALLOWED_FIELDS - {
            "external_id", "warehouse_external_id", "parent_external_id",
        }
        if unknown:
            return self.json_response({
                "status": "error",
                "message": "Unsupported field(s): %s" % ", ".join(sorted(unknown)),
            }, 400)
        external_id = payload.get("external_id")
        warehouse_external_id = payload.get("warehouse_external_id")
        name = payload.get("name")
        if not isinstance(external_id, str) or not external_id.strip() or len(external_id) > 128:
            return self.json_response({"status": "error", "message": "Invalid external_id"}, 400)
        if not isinstance(warehouse_external_id, str) or not warehouse_external_id.strip():
            return self.json_response({
                "status": "error", "message": "Invalid warehouse_external_id",
            }, 400)
        if not isinstance(name, str) or not name.strip():
            return self.json_response({"status": "error", "message": "Invalid name"}, 400)
        barcode = payload.get("barcode")
        if barcode is not None and not isinstance(barcode, str):
            return self.json_response({"status": "error", "message": "Invalid barcode"}, 400)
        parent_external_id = payload.get("parent_external_id")
        if parent_external_id is not None and (
            not isinstance(parent_external_id, str) or not parent_external_id.strip()
        ):
            return self.json_response({
                "status": "error", "message": "Invalid parent_external_id",
            }, 400)

        try:
            env = request.env
            company = system.company_id
            mapping_model = env["cool_agristock.external.id.mapping"]
            existing = mapping_model.resolve_mapping(
                company, system, "stock.location", external_id.strip(),
            )
            if existing:
                return self.json_response({
                    "status": "error", "message": "external_id already mapped",
                    "location_id": existing.res_id,
                }, 409)

            warehouse_mapping = mapping_model.resolve_mapping(
                company, system, "stock.warehouse", warehouse_external_id.strip(),
            )
            if not warehouse_mapping:
                return self.json_response({"status": "error", "message": "Warehouse not found"}, 404)
            warehouse = env["stock.warehouse"].sudo().browse(warehouse_mapping.res_id)
            if not warehouse.exists() or warehouse.company_id != company:
                return self.json_response({"status": "error", "message": "Warehouse not found"}, 404)

            parent = warehouse.lot_stock_id
            if parent_external_id:
                parent_mapping = mapping_model.resolve_mapping(
                    company, system, "stock.location", parent_external_id.strip(),
                )
                if not parent_mapping:
                    return self.json_response({
                        "status": "error", "message": "Parent location not found",
                    }, 404)
                parent = env["stock.location"].sudo().browse(parent_mapping.res_id)
                warehouse_root = warehouse.view_location_id
                ancestors = {
                    int(node) for node in (parent.parent_path or "").split("/")
                    if node.isdigit()
                }
                if (
                    not parent.exists()
                    or parent.company_id != company
                    or parent.usage != "internal"
                    or (
                        parent.id != warehouse_root.id
                        and warehouse_root.id not in ancestors
                    )
                ):
                    return self.json_response({
                        "status": "error",
                        "message": "Parent location must be internal and belong to the warehouse",
                    }, 422)
            if parent.usage != "internal" or parent.company_id != company:
                return self.json_response({
                    "status": "error", "message": "Invalid warehouse stock location",
                }, 422)

            location = env["stock.location"].sudo().create({
                "name": name.strip(),
                "location_id": parent.id,
                "usage": "internal",
                "company_id": company.id,
                "barcode": barcode.strip() if barcode else False,
            })
            mapping, created = mapping_model.create_mapping(
                company, system, "stock.location", external_id.strip(), location.id,
            )
            if not created:
                request.env.cr.rollback()
                return self.json_response({
                    "status": "error", "message": "external_id already mapped",
                    "location_id": mapping.res_id,
                }, 409)
            return self.json_response({
                "status": "success", "location_id": location.id,
                "external_id": external_id.strip(), "name": location.name,
                "complete_name": location.complete_name,
                "warehouse_external_id": warehouse_external_id.strip(),
            }, 201)
        except AccessError:
            request.env.cr.rollback()
            return self.json_response({"status": "error", "message": "Access denied"}, 403)
        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock location creation failed")
            return self.json_response(
                {"status": "error", "message": "Unable to create location"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/locations/<string:external_id>",
        type="http", auth="bearer", methods=["PATCH"],
        csrf=False, save_session=False,
    )
    def update_location(self, external_id, **kwargs):
        system, error = self._authenticate(write=True)
        if error:
            return error
        try:
            payload = json.loads(request.httprequest.get_data(as_text=True))
        except (ValueError, UnicodeDecodeError):
            return self.json_response({"status": "error", "message": "Invalid JSON"}, 400)
        if not isinstance(payload, dict):
            return self.json_response({"status": "error", "message": "Expected JSON object"}, 400)
        unknown = set(payload) - UPDATE_ALLOWED_FIELDS
        if unknown:
            return self.json_response({
                "status": "error",
                "message": "Unsupported field(s): %s" % ", ".join(sorted(unknown)),
            }, 400)
        name = payload.get("name")
        if not payload or not isinstance(name, str) or not name.strip():
            return self.json_response({"status": "error", "message": "Invalid or missing name"}, 400)
        try:
            company = system.company_id
            mapping = request.env["cool_agristock.external.id.mapping"].resolve_mapping(
                company, system, "stock.location", external_id,
            )
            if not mapping:
                return self.json_response({
                    "status": "error", "message": "No location mapped for this external_id",
                }, 404)
            location = request.env["stock.location"].sudo().browse(mapping.res_id)
            if not location.exists() or location.company_id != company or location.usage != "internal":
                return self.json_response({
                    "status": "error", "message": "No location mapped for this external_id",
                }, 404)
            location.write({"name": name.strip()})
            return self.json_response({
                "status": "success", "location_id": location.id,
                "external_id": external_id, "name": location.name,
                "complete_name": location.complete_name,
            })
        except AccessError:
            request.env.cr.rollback()
            return self.json_response({"status": "error", "message": "Access denied"}, 403)
        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock location update failed")
            return self.json_response(
                {"status": "error", "message": "Unable to update location"}, 500,
            )
