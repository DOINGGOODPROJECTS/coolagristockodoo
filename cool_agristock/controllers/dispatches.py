import hashlib
import json
import logging
import math

import psycopg2

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError
from .api_security import require_cool_agristock_api_user, resolve_authorized_external_system
from .products import SUPPORTED_UNITS as HARDCODED_UNITS

_logger = logging.getLogger(__name__)

LINE_ALLOWED_FIELDS = {"product_external_id", "quantity", "unit", "lot_external_id"}
MAX_LINES = 100


class CoolAgristockDispatchesAPI(http.Controller):

    @staticmethod
    def json_response(data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            content_type="application/json",
        )

    @staticmethod
    def _uom_root(uom):
        return int(uom.parent_path.split("/")[0])

    @staticmethod
    def _canonical_hash(external_reference, warehouse_external_id, lines):
        canonical = {
            "external_reference": external_reference,
            "warehouse_external_id": warehouse_external_id,
            "lines": sorted(
                [
                    line["product_external_id"], line["quantity"], line["unit"],
                    line.get("lot_external_id") or "",
                ]
                for line in lines
            ),
        }
        blob = json.dumps(canonical, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    @http.route(
        "/cool_agristock/api/v1/dispatches/<string:external_reference>",
        type="http",
        auth="bearer",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def get_dispatch_status(self, external_reference, **kwargs):
        if not require_cool_agristock_api_user():
            return self.json_response({
                "status": "error",
                "message": "Access denied: Cool Agristock API User role required",
            }, 403)

        try:
            external_system = resolve_authorized_external_system()
        except ValidationError as exc:
            return self.json_response({"status": "error", "message": str(exc)}, 403)

        if not external_system:
            return self.json_response({
                "status": "error",
                "message": (
                    "This API key is not authorized for transaction status "
                    "lookup: it is not bound to an active external system."
                ),
            }, 403)

        try:
            env = request.env
            transaction = env["cool_agristock.wms.transaction"].sudo().search([
                ("company_id", "=", external_system.company_id.id),
                ("external_system_id", "=", external_system.id),
                ("transaction_type", "=", "dispatch"),
                ("external_reference", "=", external_reference),
            ], limit=1)
            if not transaction:
                return self.json_response(
                    {"status": "error", "message": "Dispatch not found"}, 404,
                )
            picking = transaction.picking_id
            return self.json_response({
                "status": "success",
                "external_reference": external_reference,
                "dispatch_id": picking.id,
                "transaction_type": "dispatch",
                "state": picking.state,
                "warehouse_id": picking.picking_type_id.warehouse_id.id,
                "created_at": picking.create_date.isoformat() if picking.create_date else None,
                "validated_at": picking.date_done.isoformat() if picking.date_done else None,
            })
        except Exception:
            _logger.exception("Cool Agristock dispatch status lookup failed")
            return self.json_response(
                {"status": "error", "message": "Unable to retrieve dispatch status"}, 500,
            )

    @http.route(
        "/cool_agristock/api/v1/dispatches",
        type="http",
        auth="bearer",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def create_dispatch(self, **kwargs):

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

        has_products = "products" in payload
        has_lines = "lines" in payload

        if has_products and has_lines:
            return self.json_response({
                "status": "error",
                "message": "Specify either 'products' (legacy) or 'lines' (Phase G), not both",
            }, 400)

        if has_lines:
            return self._create_dispatch_wms_first(payload)

        return self._create_dispatch_legacy(payload)

    def _create_dispatch_legacy(self, payload):
        """Original Phase <A-era dispatch creation, byte-for-byte
        unchanged -- see controllers/receipts.py's
        _create_receipt_legacy for the same reasoning.
        """
        external_reference = payload.get("external_reference")
        warehouse_id = payload.get("warehouse_id")
        customer_id = payload.get("customer_id")
        products = payload.get("products")

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
            type(warehouse_id) is not int
            or type(customer_id) is not int
            or warehouse_id <= 0
            or customer_id <= 0
        ):
            return self.json_response({
                "status": "error",
                "message": "Invalid warehouse or customer",
            }, 400)

        if (
            not isinstance(products, list)
            or not products
            or len(products) > 100
        ):
            return self.json_response({
                "status": "error",
                "message": "Invalid products list",
            }, 400)

        try:
            env = request.env

            Picking = env["stock.picking"]
            Move = env["stock.move"]

            if (
                not Picking.has_access("create")
                or not Move.has_access("create")
            ):
                return self.json_response({
                    "status": "error",
                    "message": "Insufficient permissions",
                }, 403)

            warehouse = env["stock.warehouse"].search([
                ("id", "=", warehouse_id),
                ("company_id", "in", env.companies.ids),
            ], limit=1)

            if not warehouse:
                return self.json_response({
                    "status": "error",
                    "message": "Warehouse not found",
                }, 404)

            customer = env["res.partner"].search([
                ("id", "=", customer_id),
            ], limit=1)

            if not customer:
                return self.json_response({
                    "status": "error",
                    "message": "Customer not found",
                }, 404)

            picking_type = warehouse.out_type_id

            if (
                not picking_type
                or picking_type.code != "outgoing"
                or not picking_type.default_location_src_id
                or not picking_type.default_location_dest_id
            ):
                return self.json_response({
                    "status": "error",
                    "message": "Outgoing operation unavailable",
                }, 400)

            move_values = []
            seen_products = set()

            for line in products:

                if not isinstance(line, dict):
                    return self.json_response({
                        "status": "error",
                        "message": "Invalid product line",
                    }, 400)

                product_id = line.get("product_id")
                quantity = line.get("quantity")

                if (
                    type(product_id) is not int
                    or product_id <= 0
                    or type(quantity) not in (int, float)
                    or not math.isfinite(quantity)
                    or not (0 < quantity <= 1000000000)
                    or product_id in seen_products
                ):
                    return self.json_response({
                        "status": "error",
                        "message": "Invalid or duplicate product quantity",
                    }, 400)

                seen_products.add(product_id)

                product = env["product.product"].search([
                    ("id", "=", product_id),
                    ("company_id", "in", [False, warehouse.company_id.id]),
                ], limit=1)

                if not product:
                    return self.json_response({
                        "status": "error",
                        "message": "Product not found",
                    }, 404)

                if product.type != "consu" or not product.is_storable:
                    return self.json_response({
                        "status": "error",
                        "message": "Product must be stock-tracked",
                    }, 400)

                move_values.append({
                    "product_id": product.id,
                    "product_uom_qty": quantity,
                    "product_uom": product.uom_id.id,
                    "location_id": picking_type.default_location_src_id.id,
                    "location_dest_id": picking_type.default_location_dest_id.id,
                    "company_id": warehouse.company_id.id,
                })

            # Serialize concurrent requests for the same external
            # reference so the duplicate check below cannot race.
            # The lock is transaction-scoped and releases automatically
            # on commit or rollback.
            lock_key = int.from_bytes(
                hashlib.sha256(
                    f"cool_agristock_dispatch:{picking_type.id}:"
                    f"{external_reference}".encode()
                ).digest()[:8],
                "big",
                signed=True,
            )
            env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s)", (lock_key,)
            )

            existing = Picking.search([
                ("origin", "=", external_reference),
                ("picking_type_id", "=", picking_type.id),
            ], limit=1)

            if existing:
                return self.json_response({
                    "status": "error",
                    "message": "External reference already exists",
                    "dispatch_id": existing.id,
                }, 409)

            dispatch = Picking.create({
                "partner_id": customer.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": external_reference,
                "company_id": warehouse.company_id.id,
            })

            for values in move_values:
                values["picking_id"] = dispatch.id

            Move.create(move_values)

            return self.json_response({
                "status": "success",
                "dispatch_id": dispatch.id,
                "dispatch_reference": dispatch.name,
                "external_reference": external_reference,
                "state": dispatch.state,
            }, 201)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response({
                "status": "error",
                "message": "Access denied",
            }, 403)

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock dispatch creation failed")
            return self.json_response({
                "status": "error",
                "message": "Unable to create dispatch",
            }, 500)

    def _create_dispatch_wms_first(self, payload):
        """Phase G: fully external-ID-addressed dispatch creation --
        see controllers/receipts.py's _create_receipt_wms_first for the
        full reasoning (identical pattern, outgoing instead of incoming).
        """
        try:
            external_system = resolve_authorized_external_system()
        except ValidationError as exc:
            return self.json_response({"status": "error", "message": str(exc)}, 403)

        if not external_system:
            return self.json_response({
                "status": "error",
                "message": (
                    "This API key is not authorized for WMS-first dispatch "
                    "creation: it is not bound to an active external system."
                ),
            }, 403)

        external_reference = payload.get("external_reference")
        warehouse_external_id = payload.get("warehouse_external_id")
        lines = payload.get("lines")

        unknown_fields = set(payload.keys()) - {
            "external_reference", "warehouse_external_id", "lines",
        }
        if unknown_fields:
            return self.json_response({
                "status": "error",
                "message": "Unsupported field(s): %s" % ", ".join(sorted(unknown_fields)),
            }, 400)

        if (
            not isinstance(external_reference, str)
            or not external_reference.strip()
            or len(external_reference) > 128
        ):
            return self.json_response(
                {"status": "error", "message": "Invalid external_reference"}, 400,
            )
        external_reference = external_reference.strip()

        if not isinstance(warehouse_external_id, str) or not warehouse_external_id.strip():
            return self.json_response(
                {"status": "error", "message": "Invalid warehouse_external_id"}, 400,
            )
        warehouse_external_id = warehouse_external_id.strip()

        if not isinstance(lines, list) or not lines:
            return self.json_response(
                {"status": "error", "message": "lines must be a non-empty list"}, 400,
            )
        if len(lines) > MAX_LINES:
            return self.json_response({"status": "error", "message": "Too many lines"}, 400)

        for line in lines:
            if not isinstance(line, dict):
                return self.json_response({"status": "error", "message": "Invalid line"}, 400)
            unknown = set(line.keys()) - LINE_ALLOWED_FIELDS
            if unknown:
                return self.json_response({
                    "status": "error",
                    "message": "Unsupported line field(s): %s" % ", ".join(sorted(unknown)),
                }, 400)
            product_external_id = line.get("product_external_id")
            quantity = line.get("quantity")
            unit = line.get("unit")
            lot_external_id = line.get("lot_external_id")
            if not isinstance(product_external_id, str) or not product_external_id.strip():
                return self.json_response(
                    {"status": "error", "message": "Invalid product_external_id"}, 400,
                )
            if (
                type(quantity) not in (int, float)
                or isinstance(quantity, bool)
                or not math.isfinite(quantity)
                or not (0 < quantity <= 1000000000)
            ):
                return self.json_response(
                    {"status": "error", "message": "quantity must be a positive number"}, 400,
                )
            if not isinstance(unit, str) or not unit.strip():
                return self.json_response({"status": "error", "message": "Invalid unit"}, 400)
            if lot_external_id is not None and (
                not isinstance(lot_external_id, str) or not lot_external_id.strip()
            ):
                return self.json_response(
                    {"status": "error", "message": "Invalid lot_external_id"}, 400,
                )

        try:
            env = request.env
            company = external_system.company_id
            Mapping = env["cool_agristock.external.id.mapping"]
            UomMapping = env["cool_agristock.uom.mapping"]
            Transaction = env["cool_agristock.wms.transaction"]

            request_hash = self._canonical_hash(external_reference, warehouse_external_id, lines)

            existing = Transaction.sudo().search([
                ("company_id", "=", company.id),
                ("external_system_id", "=", external_system.id),
                ("transaction_type", "=", "dispatch"),
                ("external_reference", "=", external_reference),
            ], limit=1)
            if existing:
                return self._existing_response(existing, request_hash, external_reference, "dispatch_id")

            warehouse_mapping = Mapping.resolve_mapping(
                company, external_system, "stock.warehouse", warehouse_external_id,
            )
            if not warehouse_mapping:
                return self.json_response({"status": "error", "message": "Warehouse not found"}, 404)
            warehouse = env["stock.warehouse"].sudo().browse(warehouse_mapping.res_id)
            if not warehouse.exists() or warehouse.company_id != company:
                return self.json_response({"status": "error", "message": "Warehouse not found"}, 404)

            picking_type = warehouse.out_type_id
            if (
                not picking_type
                or picking_type.code != "outgoing"
                or not picking_type.default_location_src_id
                or not picking_type.default_location_dest_id
            ):
                return self.json_response(
                    {"status": "error", "message": "Outgoing operation unavailable"}, 400,
                )

            move_values = []
            line_summary = []
            for line in lines:
                product_external_id = line["product_external_id"].strip()
                quantity = float(line["quantity"])
                unit_code = line["unit"].strip()
                lot_external_id = line.get("lot_external_id")
                if isinstance(lot_external_id, str):
                    lot_external_id = lot_external_id.strip()

                product_mapping = Mapping.resolve_mapping(
                    company, external_system, "product.product", product_external_id,
                )
                if not product_mapping:
                    return self.json_response({
                        "status": "error",
                        "message": "Product not found: %s" % product_external_id,
                    }, 404)
                product = env["product.product"].sudo().browse(product_mapping.res_id)
                if not product.exists() or (
                    product.company_id and product.company_id != company
                ):
                    return self.json_response({
                        "status": "error",
                        "message": "Product not found: %s" % product_external_id,
                    }, 404)

                if product.type != "consu" or not product.is_storable:
                    return self.json_response({
                        "status": "error",
                        "message": "Product must be stock-tracked: %s" % product_external_id,
                    }, 400)

                if lot_external_id:
                    lot_mapping = Mapping.resolve_mapping(
                        company, external_system, "stock.lot", lot_external_id,
                    )
                    if not lot_mapping:
                        return self.json_response({
                            "status": "error",
                            "message": "Lot not found: %s" % lot_external_id,
                        }, 404)
                    lot = env["stock.lot"].sudo().browse(lot_mapping.res_id)
                    if not lot.exists() or (
                        lot.company_id and lot.company_id != company
                    ):
                        return self.json_response({
                            "status": "error",
                            "message": "Lot not found: %s" % lot_external_id,
                        }, 404)
                    if lot.product_id != product:
                        return self.json_response({
                            "status": "error",
                            "message": "Lot %s does not belong to product %s" % (
                                lot_external_id, product_external_id,
                            ),
                        }, 422)
                elif product.tracking != "none":
                    return self.json_response({
                        "status": "error",
                        "message": (
                            "Product %s requires lot/serial tracking; "
                            "lot_external_id is required for this line." % product_external_id
                        ),
                    }, 422)

                resolved_uom = UomMapping.resolve_unit(company, external_system, unit_code)
                if not resolved_uom:
                    if unit_code.lower() not in HARDCODED_UNITS:
                        return self.json_response({
                            "status": "error",
                            "message": "Unsupported unit: %r" % (unit_code,),
                        }, 400)
                    resolved_uom = env.ref(HARDCODED_UNITS[unit_code.lower()])

                product_uom = product.uom_id
                if self._uom_root(resolved_uom) != self._uom_root(product_uom):
                    return self.json_response({
                        "status": "error",
                        "message": (
                            "Unit %r is not compatible with product %s's unit (%s)" % (
                                unit_code, product_external_id, product_uom.name,
                            )
                        ),
                    }, 422)

                normalized_quantity = resolved_uom._compute_quantity(
                    quantity, product_uom, round=True,
                )

                move_values.append({
                    "product_id": product.id,
                    "product_uom_qty": normalized_quantity,
                    "product_uom": product_uom.id,
                    "location_id": picking_type.default_location_src_id.id,
                    "location_dest_id": picking_type.default_location_dest_id.id,
                    "company_id": company.id,
                })
                line_summary.append({
                    "product_external_id": product_external_id,
                    "product_id": product.id,
                    "quantity": normalized_quantity,
                    "lot_external_id": lot_external_id or None,
                })

            try:
                with env.cr.savepoint():
                    dispatch = env["stock.picking"].sudo().create({
                        "partner_id": False,
                        "picking_type_id": picking_type.id,
                        "location_id": picking_type.default_location_src_id.id,
                        "location_dest_id": picking_type.default_location_dest_id.id,
                        "origin": external_reference,
                        "company_id": company.id,
                    })
                    for values in move_values:
                        values["picking_id"] = dispatch.id
                    env["stock.move"].sudo().create(move_values)

                    transaction = Transaction.sudo().create({
                        "company_id": company.id,
                        "external_system_id": external_system.id,
                        "transaction_type": "dispatch",
                        "external_reference": external_reference,
                        "request_hash": request_hash,
                        "picking_id": dispatch.id,
                    })
            except psycopg2.IntegrityError:
                request.env.cr.rollback()
                existing = Transaction.sudo().search([
                    ("company_id", "=", company.id),
                    ("external_system_id", "=", external_system.id),
                    ("transaction_type", "=", "dispatch"),
                    ("external_reference", "=", external_reference),
                ], limit=1)
                if not existing:
                    raise
                return self._existing_response(existing, request_hash, external_reference, "dispatch_id")

            return self.json_response({
                "status": "success",
                "dispatch_id": dispatch.id,
                "dispatch_reference": dispatch.name,
                "external_reference": external_reference,
                "state": dispatch.state,
                "lines": line_summary,
            }, 201)

        except AccessError:
            request.env.cr.rollback()
            return self.json_response({"status": "error", "message": "Access denied"}, 403)

        except Exception:
            request.env.cr.rollback()
            _logger.exception("Cool Agristock WMS-first dispatch creation failed")
            return self.json_response(
                {"status": "error", "message": "Unable to create dispatch"}, 500,
            )

    def _existing_response(self, existing, request_hash, external_reference, id_field):
        if existing.request_hash == request_hash:
            return self.json_response({
                "status": "success",
                id_field: existing.picking_id.id,
                "external_reference": external_reference,
                "state": existing.picking_id.state,
                "note": "Idempotent repeat of an already-submitted transaction.",
            }, 200)
        return self.json_response({
            "status": "error",
            "message": "external_reference already used with different content",
            id_field: existing.picking_id.id,
        }, 409)
