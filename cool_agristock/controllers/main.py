import json
import logging

from odoo import http
from odoo.http import request, Response
from .api_security import require_cool_agristock_api_user

_logger = logging.getLogger(__name__)


class CoolAgristockAPI(http.Controller):

    @http.route(
        "/cool_agristock/api/v1/health",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def health_check(self, **kwargs):

        return Response(
            json.dumps({
                "status": "success",
                "service": "Cool Agristock",
                "api_version": "1.0",
                "message": "Cool Agristock API is running"
            }),
            status=200,
            content_type="application/json"
        )

    @http.route(
        "/cool_agristock/api/v1/products",
        type="http",
        auth="bearer",
        methods=["GET"],
        csrf=False,
        readonly=True,
        save_session=False,
    )
    def get_products(self, **kwargs):

        if not require_cool_agristock_api_user():
            return Response(
                json.dumps({
                    "status": "error",
                    "message": "Access denied: Cool Agristock API User role required"
                }),
                status=403,
                content_type="application/json"
            )

        try:
            products = request.env["product.product"].search(
                [],
                limit=100,
                order="id"
            )

            result = []

            for product in products:
                result.append({
                    "id": product.id,
                    "name": product.name,
                    "default_code": product.default_code or "",
                    "barcode": product.barcode or "",
                    "active": product.active,
                })

            return Response(
                json.dumps({
                    "status": "success",
                    "count": len(result),
                    "products": result
                }),
                status=200,
                content_type="application/json"
            )

        except Exception:
            _logger.exception(
                "Cool Agristock product retrieval failed"
            )

            return Response(
                json.dumps({
                    "status": "error",
                    "message": "Unable to retrieve products"
                }),
                status=500,
                content_type="application/json"
            )

    @http.route(
            "/cool_agristock/api/v1/warehouses",
            type="http",
            auth="bearer",
            methods=["GET"],
            csrf=False,
            readonly=True,
            save_session=False,
        )

    def get_warehouses(self, **kwargs):

            if not require_cool_agristock_api_user():
                return Response(
                    json.dumps({
                        "status": "error",
                        "message": "Access denied: Cool Agristock API User role required"
                    }),
                    status=403,
                    content_type="application/json"
                )

            try:
                warehouses = request.env["stock.warehouse"].search(
                    [],
                    limit=100,
                    order="id"
                )

                result = []

                for warehouse in warehouses:
                    result.append({
                            "id": warehouse.id,
                            "name": warehouse.name,
                            "code": warehouse.code,
                            "company_id": warehouse.company_id.id,
                            "company_name": warehouse.company_id.name,
                     })

                return Response(
                    json.dumps({
                            "status": "success",
                            "count": len(result),
                            "warehouses": result
                    }),
                    status=200,
                    content_type="application/json"
                )

            except Exception:
                _logger.exception(
                    "Cool Agristock warehouse retrieval failed"
                )

                return Response(
                    json.dumps({
                            "status": "error",
                            "message": "Unable to retrieve warehouses"
                    }),
                    status=500,
                    content_type="application/json"
                )

    @http.route(
        "/cool_agristock/api/v1/inventory",
        type="http",
        auth="bearer",
        methods=["GET"],
        csrf=False,
        readonly=True,
        save_session=False,
    )
    def get_inventory(self, **kwargs):

        if not require_cool_agristock_api_user():
            return Response(
                json.dumps({
                    "status": "error",
                    "message": "Access denied: Cool Agristock API User role required"
                }),
                status=403,
                content_type="application/json"
            )

        try:
            quants = request.env["stock.quant"].search(
                [
                    ("location_id.usage", "=", "internal"),
                    ("quantity", "!=", 0),
                ],
                limit=100,
                order="id",
            )

            result = []

            for quant in quants:
                result.append({
                    "product_id": quant.product_id.id,
                    "product_name": quant.product_id.name,
                    "location_id": quant.location_id.id,
                    "location_name": quant.location_id.complete_name,
                    "quantity": quant.quantity,
                    "reserved_quantity": quant.reserved_quantity,
                    "unit": quant.product_uom_id.name,
                })

            return Response(
                json.dumps({
                    "status": "success",
                    "count": len(result),
                    "inventory": result,
                }),
                status=200,
                content_type="application/json",
            )

        except Exception:
            _logger.exception("Cool Agristock inventory retrieval failed")

            return Response(
                json.dumps({
                    "status": "error",
                    "message": "Unable to retrieve inventory",
                }),
                status=500,
                content_type="application/json",
            )
