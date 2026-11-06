# -*- coding: utf-8 -*-

import functools
import logging

from odoo import api, SUPERUSER_ID
from odoo.http import request


_logger = logging.getLogger(__name__)

COOL_AGRISTOCK_API_GROUP = (
    "cool_agristock.group_cool_agristock_api_user"
)


def require_cool_agristock_api_user():
    """
    Verify that the authenticated Odoo user
    belongs to the Cool Agristock API User security group.

    Returns:
        True if authorized.
        False if unauthorized.
    """

    user = request.env.user

    if not user or not user.id:
        return False

    return user.has_group(COOL_AGRISTOCK_API_GROUP)


def resolve_authorized_external_system():
    """Server-side resolution of the external system authorized for the
    currently authenticated request. Never derived from, or trusted
    against, anything in the request body -- see
    ``cool_agristock.api.key.resolve_authorized_external_system`` for why.

    Returns:
        The authorized ``cool_agristock.external.system`` recordset (empty if
        the authenticated key isn't bound to one, or its external system
        has been deactivated since).

    Raises:
        ``odoo.exceptions.ValidationError`` if the authenticated identity
        is ambiguously bound to more than one external system.
    """

    user = request.env.user
    return request.env["cool_agristock.api.key"].sudo().resolve_authorized_external_system(user)


def _error_category_for_status(status):
    if status in (401, 403):
        return "auth_failed"
    if status == 400:
        return "validation_error"
    if status == 404:
        return "not_found"
    if status == 409:
        return "conflict"
    if status and status >= 500:
        return "server_error"
    return False


def _record_api_activity(status):
    """Best-effort activity log write. Never raises -- a logging failure
    here must never break the actual API response.

    Some routes use ``readonly=True`` (a performance choice: GET endpoints
    run on a cursor that is never committed at the end of the request).
    Writing on ``request.cr`` directly would silently vanish for those
    routes with no error at all -- confirmed directly against this
    codebase's own readonly GET endpoints. For those specifically, this
    opens its own, independently committed cursor instead. Non-readonly
    (write) routes already commit normally, so they write directly on the
    request's own cursor -- cheaper, and avoids Odoo's test harness
    refusing to open a new read/write cursor from inside a readonly one.
    """
    try:
        user = request.env.user
        company_id = request.env.company.id
        external_system_id = False
        api_key_id = False

        if user and user.id and not user._is_public():
            try:
                resolved = resolve_authorized_external_system()
                external_system_id = resolved[:1].id or False
            except Exception:
                external_system_id = False

            key = request.env["cool_agristock.api.key"].sudo().search(
                [("integration_user_id", "=", user.id)],
                limit=1, order="create_date desc",
            )
            api_key_id = key.id or False

        values = {
            "company_id": company_id,
            "external_system_id": external_system_id,
            "api_key_id": api_key_id,
            "endpoint": f"{request.httprequest.method} {request.httprequest.path}",
            "http_status": status,
            "error_category": _error_category_for_status(status),
        }

        if request.env.cr.readonly:
            with request.env.registry.cursor() as log_cr:
                log_env = api.Environment(log_cr, SUPERUSER_ID, {})
                log_env["cool_agristock.api.activity.log"].create(values)
        else:
            request.env["cool_agristock.api.activity.log"].sudo().create(values)
    except Exception:
        _logger.exception("Failed to record Cool Agristock API activity log entry")


def log_api_activity(func):
    """Route decorator: records one Cool Agristock activity log entry per
    call (method, path, final HTTP status, resolved connection if any, a
    best-effort error category), after the wrapped method returns or
    raises. Apply directly below ``@http.route(...)``:

        @http.route(...)
        @log_api_activity
        def my_endpoint(self, ...):
            ...

    Never changes the actual response -- logging is purely observational.
    """

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        status = 500
        try:
            response = func(self, *args, **kwargs)
            status = getattr(response, "status_code", 200)
            return response
        except Exception:
            status = 500
            raise
        finally:
            _record_api_activity(status)

    return wrapped
