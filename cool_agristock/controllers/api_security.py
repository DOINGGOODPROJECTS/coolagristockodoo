# -*- coding: utf-8 -*-

from odoo.http import request


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
