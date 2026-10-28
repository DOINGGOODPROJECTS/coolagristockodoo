import uuid

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class CoolAgristockApiKey(models.Model):
    _name = "cool_agristock.api.key"
    _description = "Cool Agristock API Key"
    _order = "create_date desc"

    name = fields.Char(
        string="Integration Name",
        required=True,
        help="A label for the WMS integration this key is used by, "
             "e.g. 'Main Warehouse Integration'.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    integration_user_id = fields.Many2one(
        "res.users",
        string="Integration Identity",
        readonly=True,
        help="The dedicated, password-less Odoo user this key authenticates "
             "as when calling the Cool Agristock REST API.",
    )

    apikey_id = fields.Many2one(
        "res.users.apikeys",
        string="API Key Record",
        ondelete="set null",
        readonly=True,
        copy=False,
    )

    expiration_date = fields.Datetime(
        string="Expiration Date",
        readonly=True,
    )

    never_expires = fields.Boolean(
        string="Never Expires",
        readonly=True,
    )

    revoked_date = fields.Datetime(
        string="Revoked On",
        readonly=True,
        copy=False,
    )

    external_system_id = fields.Many2one(
        "cool_agristock.external.system",
        string="Authorized External System",
        readonly=True,
        help="If set, this key's integration identity is authorized to "
             "use write operations that require a resolved external "
             "system (e.g. product synchronization). Existing keys with "
             "no value here are unaffected: they keep working exactly as "
             "before for every endpoint that doesn't require this "
             "binding. Set only at key generation time, via the Generate "
             "API Key wizard -- never editable afterward, matching this "
             "model's existing read-only-after-creation form.",
    )

    state = fields.Selection(
        [
            ("active", "Active"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        string="Status",
        compute="_compute_state",
        # Deliberately not stored: "expired" depends on the current time,
        # not just on this record's own fields, so a stored value would
        # stay "Active" forever past expiration until something happened
        # to write to the record and trigger a recompute. Computing fresh
        # on every read keeps the displayed status honest.
    )

    @api.depends("apikey_id", "expiration_date", "revoked_date")
    def _compute_state(self):
        now = fields.Datetime.now()

        for record in self:
            if record.revoked_date or not record.apikey_id:
                record.state = "revoked"
            elif record.expiration_date and record.expiration_date <= now:
                record.state = "expired"
            else:
                record.state = "active"

    @api.constrains("company_id", "external_system_id")
    def _check_external_system_company(self):
        for record in self:
            if (
                record.external_system_id
                and record.external_system_id.company_id != record.company_id
            ):
                raise ValidationError(_(
                    "The authorized external system must belong to the "
                    "same company as the API key."
                ))

    @api.constrains("integration_user_id", "external_system_id")
    def _check_dedicated_identity_for_bound_keys(self):
        """Defense-in-depth for the authorization-isolation fix in
        generate_key(): a bound key's integration_user_id must never be
        shared with any other cool_agristock.api.key record, bound or not.

        generate_key() itself already guarantees this for every key it
        creates (a bound key always gets a freshly-created, never-reused
        user). This constraint exists for paths that bypass generate_key()
        entirely -- a direct ORM write (e.g. from a future migration
        script, or an administrator using Odoo's developer tools) that
        tried to reuse an existing user for a bound key, or to bind a
        key that still shares the old per-company shared user. Either
        would silently reintroduce the exact vulnerability fixed above.
        """
        for record in self:
            if not record.external_system_id or not record.integration_user_id:
                continue

            sharing = self.sudo().search([
                ("integration_user_id", "=", record.integration_user_id.id),
                ("id", "!=", record.id),
            ])
            if sharing:
                raise ValidationError(_(
                    "A key bound to an external system must have its "
                    "own dedicated integration identity -- it cannot "
                    "share an integration user with any other API key."
                ))

    def _check_can_manage(self, company=None):
        """Raise unless the current user is a Cool Agristock Administrator for
        ``company`` (or, called on a recordset, for every record's
        company)."""
        admin_group = self.env.ref(
            "cool_agristock.group_cool_agristock_administrator"
        )

        if admin_group not in self.env.user.all_group_ids:
            raise AccessError(_(
                "Only Cool Agristock Administrators can manage API keys."
            ))

        companies = [company] if company is not None else self.mapped("company_id")

        for record_company in companies:
            if record_company not in self.env.user.company_ids:
                raise AccessError(_(
                    "You do not have access to API keys for this company."
                ))

    @api.model
    def _get_or_create_integration_user(self, company):
        """Return the dedicated, password-less Odoo user that Cool Agristock API
        keys for ``company`` authenticate as, creating it on first use.

        This user is never given a usable password and no invitation email
        is sent, so it cannot log in interactively. It exists purely so
        Bearer API keys have an identity to attach to, matching Odoo's own
        design (``res.users.apikeys`` rows always belong to a user).
        """
        xml_id = f"integration_user_company_{company.id}"
        full_xml_id = f"cool_agristock.{xml_id}"

        user = self.env.ref(full_xml_id, raise_if_not_found=False)

        if user:
            return user.sudo()

        api_group = self.env.ref(
            "cool_agristock.group_cool_agristock_api_user"
        )
        internal_group = self.env.ref("base.group_user")

        user = self.env["res.users"].sudo().create({
            "name": f"Cool Agristock API Service ({company.name})",
            "login": f"cool_agristock-api-service-{company.id}@cool_agristock.local",
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
            "group_ids": [(6, 0, [internal_group.id, api_group.id])],
        })

        self.env["ir.model.data"].sudo().create({
            "name": xml_id,
            "module": "cool_agristock",
            "model": "res.users",
            "res_id": user.id,
            "noupdate": True,
        })

        return user

    @api.model
    def _create_dedicated_integration_user(self, company, external_system):
        """Create a fresh, single-purpose integration user for a key
        bound to ``external_system``.

        **Security fix, not a style choice.** Every key sharing the
        single per-company user returned by
        ``_get_or_create_integration_user`` shares one authentication
        identity -- and Odoo's Bearer-token check only ever reports
        *which user* authenticated, never which specific
        ``res.users.apikeys`` row matched (confirmed directly against
        this Odoo 19 installation's ``_check_apikey_credentials``).
        Before this fix, binding *any* key for a company to an external
        system silently authorized *every other key* sharing that
        company's user too -- including keys deliberately generated with
        no binding at all. Reproduced directly: an unbound key
        authenticated a product-write request and succeeded (`201`)
        when it should have been rejected (`403`). See
        docs/EXTERNAL_ID_MAPPING.md's "API key binding" section for the
        full writeup.

        The fix: a key that requests a binding gets its **own** user,
        never shared with any other key. A bearer token now maps to
        exactly one user, which maps to exactly one ``cool_agristock.api.key``
        record (enforced below), which resolves to exactly one external
        system -- the "authorized external system is derived from the
        exact bearer token presented" property the security review
        requires.

        Unbound keys are entirely unaffected: they keep calling
        ``_get_or_create_integration_user`` exactly as before, so this
        fix introduces zero behavior change for any key that doesn't
        request a binding -- including every key already covered by
        ``test_multiple_keys_share_one_integration_identity``, which
        never requests one.
        """
        api_group = self.env.ref(
            "cool_agristock.group_cool_agristock_api_user"
        )
        internal_group = self.env.ref("base.group_user")

        suffix = uuid.uuid4().hex[:12]

        return self.env["res.users"].sudo().create({
            "name": f"Cool Agristock API Service ({company.name} / {external_system.name})",
            "login": f"cool_agristock-api-service-{company.id}-{suffix}@cool_agristock.local",
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
            "group_ids": [(6, 0, [internal_group.id, api_group.id])],
        })

    @api.model
    def generate_key(self, name, company, expiration_date=None, external_system=None):
        """Create a new Cool Agristock API key for ``company``.

        :param str name: integration label shown in the UI.
        :param res.company company: the owning company.
        :param datetime.datetime|None expiration_date: ``None`` means the
            key never expires.
        :param cool_agristock.external.system|None external_system: if given,
            binds this key's integration identity to that external
            system, authorizing it for write operations that require a
            resolved external system (e.g. product synchronization).
            Optional and ``None`` by default -- omitting it behaves
            exactly as before this parameter existed.
        :returns: tuple of (the raw API key, the created cool_agristock.api.key
            record). The raw key is returned exactly once and is never
            stored anywhere.
        """
        self._check_can_manage(company=company)

        if external_system and external_system.company_id != company:
            raise ValidationError(_(
                "The authorized external system must belong to the same "
                "company as the API key."
            ))

        # Security fix: a key requesting a binding must never share an
        # integration user with any other key -- see
        # _create_dedicated_integration_user()'s docstring for why.
        # Unbound keys are unaffected, continuing to share the one
        # per-company user exactly as before.
        if external_system:
            integration_user = self._create_dedicated_integration_user(
                company, external_system
            )
        else:
            integration_user = self._get_or_create_integration_user(company)

        ApiKeys = self.env["res.users.apikeys"]

        raw_key = (
            ApiKeys.with_user(integration_user)
            .sudo()
            ._generate(scope=None, name=name, expiration_date=expiration_date)
        )

        # _generate() only returns the raw key, not the created row's id.
        # The row's "index" column is the key's first 8 hex characters
        # (see INDEX_SIZE in odoo/addons/base/models/res_users.py), which is
        # how Odoo itself looks keys up, so it reliably identifies the row
        # just inserted without depending on the (user-chosen, possibly
        # reused) integration name.
        self.env.cr.execute(
            """
            SELECT id FROM res_users_apikeys
            WHERE user_id = %s AND index = %s
            """,
            (integration_user.id, raw_key[:8]),
        )
        apikey_row = self.env.cr.fetchone()
        apikey_record = ApiKeys.sudo().browse(
            apikey_row[0] if apikey_row else []
        )

        record = self.sudo().create({
            "name": name,
            "company_id": company.id,
            "integration_user_id": integration_user.id,
            "apikey_id": apikey_record.id,
            "expiration_date": expiration_date,
            "never_expires": not expiration_date,
            "external_system_id": external_system.id if external_system else False,
        })

        return raw_key, record

    @api.model
    def resolve_authorized_external_system(self, user):
        """Server-side resolution of the external system authorized for
        the currently authenticated ``user`` -- never trust an
        ``external_system_id`` supplied by an API client directly.

        Why this resolves from ``user`` rather than from "the specific
        key that authenticated": Odoo's own Bearer token verification
        (``_check_apikey_credentials``) only returns the matching user
        id, not which ``res.users.apikeys`` row matched -- and several
        ``cool_agristock.api.key`` records can share one integration user per
        company (see ``_get_or_create_integration_user``), by existing,
        tested, unchanged design. So in practice every key sharing one
        company's integration user shares one authorization outcome:
        whichever bound, active key(s) exist for that identity.

        :returns: the authorized, active ``cool_agristock.external.system``
            recordset (empty if none is authorized).
        :raises ValidationError: if two bound keys for the same identity
            resolve to *different* external systems -- a misconfigured,
            ambiguous state that must be surfaced, never silently
            resolved by guessing one.
        """
        candidates = self.sudo().search([
            ("integration_user_id", "=", user.id),
            ("external_system_id", "!=", False),
        ])

        # state is a non-stored compute (see _compute_state) -- filter in
        # Python rather than via a search domain, and likewise exclude
        # any external system that has since been deactivated.
        authorized = candidates.filtered(
            lambda rec: rec.state == "active" and rec.external_system_id.active
        ).mapped("external_system_id")

        if len(authorized) > 1:
            raise ValidationError(_(
                "This integration identity is bound to more than one "
                "active external system -- this is a misconfiguration "
                "that must be resolved by an administrator before "
                "write operations can proceed."
            ))

        return authorized

    def action_revoke(self):
        self._check_can_manage()

        for record in self:
            if record.state == "revoked":
                continue

            if record.apikey_id:
                record.apikey_id.sudo()._remove()

            record.write({
                "revoked_date": fields.Datetime.now(),
            })

        return True

    def action_create_replacement(self):
        """Open the generate wizard pre-filled from an expired or revoked
        key, so replacing it doesn't mean re-typing the integration name
        and expiration policy from scratch."""
        self.ensure_one()
        self._check_can_manage()

        return {
            "type": "ir.actions.act_window",
            "res_model": "cool_agristock.api.key.generate.wizard",
            "name": _("Generate Replacement API Key"),
            "views": [(
                self.env.ref(
                    "cool_agristock.view_cool_agristock_api_key_generate_wizard_form"
                ).id,
                "form",
            )],
            "target": "new",
            "context": {
                "default_name": self.name,
                "default_company_id": self.company_id.id,
                "default_never_expires": self.never_expires,
                "default_external_system_id": self.external_system_id.id,
            },
        }
