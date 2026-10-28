import type { Dictionary } from "@/types/content";

const GITHUB_REPO = "https://github.com/DOINGGOODPROJECTS/coolagristockodoo";
const DOCS_BASE = `${GITHUB_REPO}/blob/19.0/docs`;

export const en: Dictionary = {
  meta: {
    siteName: "Cool Agristock",
    home: {
      title: "Cool Agristock — Odoo Warehouse Integration (Free & Open-Source)",
      description:
        "Free, open-source Odoo 19 application connecting compatible external warehouse management systems (WMS) to Odoo Inventory via a documented REST API.",
    },
    product: {
      title: "Product Overview — Cool Agristock",
      description:
        "Odoo 19 compatibility, REST API capabilities, authentication, supported operations, and current limitations of Cool Agristock.",
    },
    services: {
      title: "Professional Services — Cool Agristock",
      description:
        "Optional, paid professional services for Cool Agristock: installation, WMS integration, custom adapters, workflow customization, and support.",
    },
    documentation: {
      title: "Documentation — Cool Agristock",
      description: "Installation guides, API reference, and support resources for Cool Agristock.",
    },
    contact: {
      title: "Contact — Cool Agristock Integration Support",
      description: "Request integration support for Cool Agristock.",
    },
  },
  nav: {
    home: "Home",
    product: "Product",
    services: "Services",
    documentation: "Documentation",
    contact: "Contact",
    downloadFree: "Download Free",
    switchLabel: "Français",
  },
  footer: {
    tagline: "A free, open-source Odoo 19 application connecting external WMS software to Odoo Inventory.",
    freeOpenSource: "Free and open-source (LGPL-3.0) — no license fee, ever.",
    githubLabel: "View source on GitHub",
    rights: "This website promotes Cool Agristock; it is independent of the Odoo addon itself.",
  },
  home: {
    hero: {
      headline: "Connect Your Warehouse Management System to Odoo",
      subheadline:
        "Cool Agristock is a free, open-source integration application that enables compatible external warehouse management systems to exchange inventory information with Odoo 19.",
      downloadCta: "Download Free",
      requestCta: "Request Integration Support",
    },
    problem: {
      title: "The Problem",
      intro: "Many agribusinesses run their warehouse operations and their ERP as two disconnected systems.",
      items: [
        "Disconnected warehouse and ERP systems, each with its own view of stock",
        "Repeated manual data entry — the same receipt or dispatch typed twice",
        "Inventory information spread across systems with no single source of truth",
        "Difficulty integrating existing WMS software with Odoo without custom development",
      ],
    },
    solution: {
      title: "The Solution",
      description:
        "Cool Agristock exposes a REST API on top of Odoo 19 Inventory. Your existing WMS calls this API to read product, warehouse, and stock data, and to create and validate receipts and dispatches.",
      diagram: {
        wms: "External WMS",
        api: "REST API",
        connector: "Cool Agristock",
        odoo: "Odoo 19 Inventory",
      },
      initiatedNote:
        "Every request is initiated by the external WMS. Cool Agristock never calls out to your WMS — there is no scheduled or automatic synchronization.",
    },
    features: {
      title: "Key Features",
      items: [
        "Product, warehouse, and supplier synchronization, addressed by your own external IDs",
        "Unit-of-measure mapping for units Odoo doesn't ship with by default",
        "Lot and serial number synchronization for traceable products",
        "Inventory visibility (on-hand stock) and staged inventory import for human review",
        "Incoming receipts — create and validate, including lot/serial-tracked products",
        "Outgoing dispatches — create and validate, including lot/serial-tracked products",
        "Transaction status lookup by your own external reference",
        "Self-service API key management",
        "Bearer-token authentication, role-based access control, and multi-company isolation",
      ],
    },
    howItWorks: {
      title: "How It Works",
      steps: [
        "Install Cool Agristock from the Odoo Apps Marketplace.",
        "Generate an API key from Cool Agristock → API Management.",
        "Configure your existing, compatible external WMS with the API base URL and key.",
        "Exchange supported warehouse information: products, warehouses, suppliers, UOM mappings, lots and serial numbers, inventory imports, receipts, dispatches, and transaction status.",
      ],
    },
    services: {
      title: "Professional Services",
      intro:
        "Cool Agristock itself is always free. For businesses that want hands-on help, optional paid services are available separately.",
      items: [
        { name: "Odoo Installation and Configuration", description: "Getting Cool Agristock installed and configured on your Odoo 19 instance." },
        { name: "WMS Integration", description: "Connecting your specific WMS to the documented REST API." },
        { name: "Custom WMS Adapter Development", description: "Building a translation layer for a WMS that doesn't speak the API natively." },
        { name: "Technical Support and Maintenance", description: "Ongoing assistance beyond best-effort community support." },
      ],
      link: "See all professional services",
    },
    cta: {
      title: "Ready to connect your warehouse to Odoo?",
      description: "The application is free to download and self-host. Integration help is optional.",
      downloadCta: "Download Free",
      requestCta: "Request Integration Support",
    },
  },
  product: {
    title: "Product Overview",
    intro:
      "Cool Agristock integrates an existing, compatible external WMS with Odoo 19's Inventory app through a REST API.",
    overview: {
      title: "What it is",
      body: "Cool Agristock is not itself a warehouse management system. It does not manage racking, picking routes, or barcode scanning hardware — it is the integration layer between an existing WMS and Odoo's Inventory app. The external WMS calls this API to read Odoo's product, warehouse, and stock data, and to push incoming receipts and outgoing dispatches into Odoo's standard stock workflow.",
    },
    version: {
      title: "Supported Odoo version",
      body: "Odoo 19. Cool Agristock depends on four Odoo Community Association (OCA) modules — component, component_event, connector, and queue_job — which are bundled inside the Odoo Apps Marketplace download, so no separate installation step is needed for a marketplace install.",
    },
    architecture: {
      title: "Integration architecture",
      body: "Every request in this integration is initiated by the external WMS; Odoo never calls out to the WMS. All data ultimately lives in Odoo's own PostgreSQL database — Cool Agristock adds no separate datastore.",
      diagram: {
        wms: "External WMS",
        api: "HTTPS + API key",
        connector: "Cool Agristock",
        odoo: "Odoo 19 Inventory",
        db: "PostgreSQL",
      },
    },
    api: {
      title: "REST API capabilities",
      body: "Cool Agristock exposes a versioned REST API rooted at /cool_agristock/api/v1. All controller-level responses share a consistent {\"status\": \"success\" | \"error\", ...} shape.",
      capabilities: [
        "GET /health — public health check, no authentication required",
        "GET /products — retrieve up to 100 products; POST /products and PATCH /products/{external_id} — create and update products",
        "GET /warehouses — retrieve warehouses; POST /warehouses and PATCH /warehouses/{external_id} — create and update warehouses",
        "GET /suppliers, POST /suppliers, and PATCH /suppliers/{external_id} — retrieve, create, and update suppliers",
        "GET /inventory — retrieve on-hand stock quantities",
        "GET /lots, POST /lots, and PATCH /lots/{external_id} — retrieve, create, and resolve lots and serial numbers",
        "POST /inventory-adjustments — stage an initial inventory count for human review inside Odoo",
        "POST /receipts and /receipts/{id}/validate — create and validate incoming receipts, including lot/serial-tracked products",
        "GET /receipts/{external_reference} — look up a receipt's status by your own external reference",
        "POST /dispatches and /dispatches/{id}/validate — create and validate outgoing dispatches, including lot/serial-tracked products",
        "GET /dispatches/{external_reference} — look up a dispatch's status by your own external reference",
      ],
    },
    auth: {
      title: "Authentication and access control",
      body: "Every protected endpoint requires an Authorization: Bearer header carrying a real Odoo API key. Keys are generated and managed self-service, inside Odoo, by users in the Cool Agristock Administrator group — no developer involvement needed. The authenticated key's underlying user must also belong to the Cool Agristock API User group to call the API. API key records are isolated per company by record rules.",
    },
    operations: {
      title: "Supported inventory operations",
      items: [
        "Read product, warehouse, supplier, and inventory data",
        "Create and update products, warehouses, and suppliers, addressed by your own external IDs",
        "Configure unit-of-measure mappings for units Odoo doesn't ship with by default",
        "Create and resolve lots and serial numbers for traceable products",
        "Stage initial inventory observations for human review — these are never applied to real stock automatically; an Inventory Manager must review and apply them manually from Odoo's own Inventory Adjustment screen",
        "Create a draft incoming receipt, then validate it against received quantities, including lot/serial-tracked products",
        "Create a draft outgoing dispatch, then validate it against dispatched quantities, including lot/serial-tracked products",
        "Look up the status of a receipt or dispatch by your own external reference",
        "Duplicate-transaction protection via a PostgreSQL advisory lock on each external reference",
      ],
    },
    limitations: {
      title: "Current limitations",
      items: [
        "No pagination on the products, warehouses, or inventory list endpoints (capped at 100 records)",
        "No per-warehouse access control within a company",
        "Partial receipts and partial dispatches are not supported — quantities must match exactly",
        "Initial inventory imports are staged for human review — applying a reviewed count to actual Odoo stock still requires one manual step in Odoo's own Inventory Adjustment screen, by design",
        "No automatic or scheduled synchronization — every request is initiated by the external WMS",
        "No built-in, WMS-specific adapters — this is one generic REST API",
      ],
    },
    screenshots: {
      title: "Screenshots",
      items: [
        {
          src: "/images/screenshot_apps_listing.png",
          alt: "Cool Agristock listed in Odoo's Apps screen",
          caption: "Cool Agristock listed in Odoo's Apps screen.",
        },
        {
          src: "/images/screenshot_api_management.png",
          alt: "Cool Agristock API Management screen listing a self-service API key",
          caption:
            "The API Management screen, where an authorized business user generates, views, and revokes their own API keys.",
        },
        {
          src: "/images/screenshot_api_health.png",
          alt: "Cool Agristock REST API health check response",
          caption: "The REST API's health check endpoint, confirmed live and responding.",
        },
      ],
    },
  },
  services: {
    title: "Professional Services",
    intro:
      "Cool Agristock's software is, and always will be, free and open-source. These optional, paid services are performed by people, for businesses that want hands-on help beyond what's in the documentation.",
    freeNote:
      "Nothing below unlocks functionality that is otherwise withheld — every documented REST API capability is already free. These are services, not software license tiers.",
    packages: [
      {
        name: "1. Odoo Installation and Configuration",
        description:
          "Installing Cool Agristock and its bundled OCA dependencies on your Odoo 19 instance, assigning user permissions, and generating the first API key.",
      },
      {
        name: "2. Basic WMS Integration",
        description:
          "Configuring your existing WMS against Cool Agristock's REST API when it already speaks a compatible protocol, and validating the connection end-to-end.",
      },
      {
        name: "3. Custom WMS Adapter Development",
        description:
          "Building a translation layer between your WMS's native protocol and Cool Agristock's REST API, for WMS software that can't speak it directly.",
      },
      {
        name: "4. Inventory Workflow Customization",
        description:
          "Adapting how receipts and dispatches map to your specific operational process, within what Odoo's stock workflow supports.",
      },
      {
        name: "5. Technical Support and Maintenance",
        description:
          "Ongoing, dedicated assistance beyond best-effort community support, for businesses that want continuity after their integration is live.",
      },
    ],
    optionalNote: "Every service above is entirely optional. Using Cool Agristock yourself, for free, remains fully supported.",
    noPricingNote:
      "Pricing is discussed per request and depends on scope — no price list is published here.",
    cta: "Request Integration Support",
  },
  documentation: {
    title: "Documentation",
    intro:
      "Full documentation lives in the project's GitHub repository, alongside the source code.",
    links: [
      {
        label: "Installation Guide",
        href: `${DOCS_BASE}/INSTALLATION.md`,
        description: "Step-by-step install instructions for business users, no Odoo development experience required.",
        external: true,
      },
      {
        label: "Quick Start Guide",
        href: `${DOCS_BASE}/QUICK_START.md`,
        description: "The fastest path through the whole workflow, with a minimal working example.",
        external: true,
      },
      {
        label: "Guide de démarrage rapide (French)",
        href: `${DOCS_BASE}/QUICK_START_FR.md`,
        description: "French translation of the Quick Start Guide.",
        external: true,
      },
      {
        label: "WMS Integration Guide",
        href: `${DOCS_BASE}/WMS_INTEGRATION.md`,
        description: "Architecture, authentication, every endpoint with request/response examples, and error handling.",
        external: true,
      },
      {
        label: "API Reference",
        href: `${DOCS_BASE}/API.md`,
        description: "The complete, field-by-field technical specification of every endpoint.",
        external: true,
      },
      {
        label: "Customer Support",
        href: `${DOCS_BASE}/SUPPORT.md`,
        description: "How to report installation/API issues, bugs, and feature requests.",
        external: true,
      },
    ],
  },
  contact: {
    title: "Contact — Integration Support",
    intro:
      "Use this form to describe your integration needs. Fields marked are used to assess technical compatibility before any work is proposed.",
    formDisabledTitle: "Form submission is not yet connected",
    formDisabledBody:
      "This form validates your input, but sending it is not yet enabled — no backend or form-delivery service has been configured for this site yet. Submitting will not send your information anywhere. Until this is enabled, please use the contact channel below instead.",
    fields: {
      companyName: "Company name",
      contactName: "Contact name",
      email: "Business email",
      country: "Country",
      existingErp: "Existing ERP",
      existingWms: "Existing WMS",
      requiredIntegration: "Required integration",
      projectDescription: "Project description",
    },
    submit: "Submit (not yet available)",
    privacyTitle: "Privacy",
    privacyBody:
      "This form does not store any data in your browser or transmit it anywhere while submission is disabled. Once a real delivery method is configured, this notice will be updated to explain exactly what happens to submitted information.",
    alternateContact: "In the meantime, see the Customer Support guide for how to reach the project on GitHub.",
  },
};
