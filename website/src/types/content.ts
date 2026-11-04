export type Lang = "en" | "fr";

export interface ServiceItem {
  name: string;
  description: string;
}

export interface ScreenshotItem {
  src: string;
  alt: string;
  caption: string;
}

export interface DocLink {
  label: string;
  href: string;
  description: string;
  external: boolean;
}

export interface Dictionary {
  meta: {
    siteName: string;
    home: { title: string; description: string };
    product: { title: string; description: string };
    services: { title: string; description: string };
    documentation: { title: string; description: string };
    contact: { title: string; description: string };
  };
  nav: {
    home: string;
    product: string;
    services: string;
    documentation: string;
    contact: string;
    downloadFree: string;
    switchLabel: string;
  };
  footer: {
    tagline: string;
    freeOpenSource: string;
    githubLabel: string;
    rights: string;
  };
  home: {
    hero: {
      headline: string;
      subheadline: string;
      downloadCta: string;
      requestCta: string;
    };
    problem: {
      title: string;
      intro: string;
      items: string[];
    };
    solution: {
      title: string;
      description: string;
      diagram: { wms: string; api: string; connector: string; odoo: string };
      initiatedNote: string;
    };
    video: {
      title: string;
      description: string;
      youtubeId: string;
    };
    features: {
      title: string;
      items: string[];
    };
    howItWorks: {
      title: string;
      steps: string[];
    };
    services: {
      title: string;
      intro: string;
      items: ServiceItem[];
      link: string;
    };
    cta: {
      title: string;
      description: string;
      downloadCta: string;
      requestCta: string;
    };
  };
  product: {
    title: string;
    intro: string;
    overview: { title: string; body: string };
    version: { title: string; body: string };
    architecture: {
      title: string;
      body: string;
      diagram: { wms: string; api: string; connector: string; odoo: string; db: string };
    };
    api: { title: string; body: string; capabilities: string[] };
    auth: { title: string; body: string };
    operations: { title: string; items: string[] };
    limitations: { title: string; items: string[] };
    screenshots: { title: string; items: ScreenshotItem[] };
  };
  services: {
    title: string;
    intro: string;
    freeNote: string;
    packages: ServiceItem[];
    optionalNote: string;
    noPricingNote: string;
    cta: string;
  };
  documentation: {
    title: string;
    intro: string;
    links: DocLink[];
  };
  contact: {
    title: string;
    intro: string;
    formDisabledTitle: string;
    formDisabledBody: string;
    fields: {
      companyName: string;
      contactName: string;
      email: string;
      country: string;
      existingErp: string;
      existingWms: string;
      requiredIntegration: string;
      projectDescription: string;
    };
    submit: string;
    privacyTitle: string;
    privacyBody: string;
    alternateContact: string;
  };
}
