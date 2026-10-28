import type { Dictionary } from "@/types/content";

const GITHUB_REPO = "https://github.com/DOINGGOODPROJECTS/coolagristockodoo";
const DOCS_BASE = `${GITHUB_REPO}/blob/19.0/docs`;

export const fr: Dictionary = {
  meta: {
    siteName: "AgriWare Connector",
    home: {
      title: "AgriWare Connector — Intégration d'entrepôt pour Odoo (gratuit et open-source)",
      description:
        "Application Odoo 19 gratuite et open-source qui connecte un système de gestion d'entrepôt (WMS) externe compatible à Odoo Inventaire via une API REST documentée.",
    },
    product: {
      title: "Présentation du produit — AgriWare Connector",
      description:
        "Compatibilité Odoo 19, capacités de l'API REST, authentification, opérations prises en charge et limitations actuelles d'AgriWare Connector.",
    },
    services: {
      title: "Services professionnels — AgriWare Connector",
      description:
        "Services professionnels optionnels et payants pour AgriWare Connector : installation, intégration WMS, adaptateurs personnalisés et support.",
    },
    documentation: {
      title: "Documentation — AgriWare Connector",
      description: "Guides d'installation, référence API et ressources de support pour AgriWare Connector.",
    },
    contact: {
      title: "Contact — Assistance intégration AgriWare Connector",
      description: "Demander une assistance pour l'intégration d'AgriWare Connector.",
    },
  },
  nav: {
    home: "Accueil",
    product: "Produit",
    services: "Services",
    documentation: "Documentation",
    contact: "Contact",
    downloadFree: "Télécharger gratuitement",
    switchLabel: "English",
  },
  footer: {
    tagline: "Une application Odoo 19 gratuite et open-source qui connecte un WMS externe à l'Inventaire Odoo.",
    freeOpenSource: "Gratuit et open-source (LGPL-3.0) — sans frais de licence, jamais.",
    githubLabel: "Voir le code source sur GitHub",
    rights: "Ce site fait la promotion d'AgriWare Connector ; il est indépendant du module Odoo lui-même.",
  },
  home: {
    hero: {
      headline: "Connectez votre système de gestion d'entrepôt à Odoo",
      subheadline:
        "AgriWare Connector est une application d'intégration gratuite et open-source qui permet à un système de gestion d'entrepôt (WMS) externe compatible d'échanger des informations de stock avec Odoo 19.",
      downloadCta: "Télécharger gratuitement",
      requestCta: "Demander une assistance intégration",
    },
    problem: {
      title: "Le problème",
      intro: "De nombreuses agro-industries font fonctionner leur entrepôt et leur ERP comme deux systèmes déconnectés.",
      items: [
        "Systèmes d'entrepôt et ERP déconnectés, chacun avec sa propre vision du stock",
        "Double saisie manuelle — la même réception ou expédition tapée deux fois",
        "Informations de stock dispersées entre plusieurs systèmes, sans source unique de vérité",
        "Difficulté à intégrer un WMS existant à Odoo sans développement sur mesure",
      ],
    },
    solution: {
      title: "La solution",
      description:
        "AgriWare Connector expose une API REST au-dessus de l'Inventaire Odoo 19. Votre WMS existant appelle cette API pour lire les données de produits, d'entrepôts et de stocks, et pour créer et valider les réceptions et expéditions.",
      diagram: {
        wms: "WMS externe",
        api: "API REST",
        connector: "AgriWare Connector",
        odoo: "Odoo 19 Inventaire",
      },
      initiatedNote:
        "Chaque requête est initiée par le WMS externe. AgriWare Connector n'appelle jamais votre WMS — il n'y a aucune synchronisation automatique ou planifiée.",
    },
    features: {
      title: "Fonctionnalités clés",
      items: [
        "Synchronisation des produits, entrepôts et fournisseurs, identifiés par vos propres identifiants externes",
        "Configuration des correspondances d'unités de mesure pour les unités non fournies par défaut dans Odoo",
        "Synchronisation des lots et numéros de série pour les produits traçables",
        "Visibilité du stock disponible et import d'inventaire initial mis en attente pour révision humaine",
        "Réceptions entrantes — création et validation, y compris pour les produits suivis par lot ou numéro de série",
        "Expéditions sortantes — création et validation, y compris pour les produits suivis par lot ou numéro de série",
        "Consultation du statut d'une transaction par votre propre référence externe",
        "Gestion autonome des clés API",
        "Authentification par jeton Bearer, contrôle d'accès par rôle et isolation multi-entreprise",
      ],
    },
    howItWorks: {
      title: "Comment ça marche",
      steps: [
        "Installez AgriWare Connector depuis la marketplace Odoo Apps.",
        "Générez une clé API depuis AgriWare Connector → API Management.",
        "Configurez votre WMS externe compatible avec l'URL de base de l'API et la clé.",
        "Échangez les informations d'entrepôt prises en charge : produits, entrepôts, fournisseurs, correspondances d'unités de mesure, lots et numéros de série, imports d'inventaire, réceptions, expéditions et statut des transactions.",
      ],
    },
    services: {
      title: "Services professionnels",
      intro:
        "AgriWare Connector lui-même reste toujours gratuit. Pour les entreprises qui souhaitent un accompagnement, des services payants optionnels sont proposés séparément.",
      items: [
        { name: "Installation et configuration Odoo", description: "Installation et configuration d'AgriWare Connector sur votre instance Odoo 19." },
        { name: "Intégration WMS", description: "Connexion de votre WMS spécifique à l'API REST documentée." },
        { name: "Développement d'adaptateur WMS personnalisé", description: "Construction d'une couche de traduction pour un WMS qui ne parle pas nativement l'API." },
        { name: "Support technique et maintenance", description: "Assistance continue au-delà du support communautaire." },
      ],
      link: "Voir tous les services professionnels",
    },
    cta: {
      title: "Prêt à connecter votre entrepôt à Odoo ?",
      description: "L'application est gratuite à télécharger et à auto-héberger. L'assistance à l'intégration est optionnelle.",
      downloadCta: "Télécharger gratuitement",
      requestCta: "Demander une assistance intégration",
    },
  },
  product: {
    title: "Présentation du produit",
    intro:
      "AgriWare Connector intègre un WMS externe existant et compatible avec l'application Inventaire d'Odoo 19, via une API REST.",
    overview: {
      title: "Ce que c'est",
      body: "AgriWare Connector n'est pas lui-même un système de gestion d'entrepôt. Il ne gère ni le rayonnage, ni les circuits de préparation, ni le matériel de lecture de codes-barres — c'est la couche d'intégration entre un WMS existant et le module Inventaire d'Odoo. Le WMS externe appelle cette API pour lire les données de produits, d'entrepôts et de stocks d'Odoo, et pour transmettre les réceptions entrantes et expéditions sortantes dans le flux de stock standard d'Odoo.",
    },
    version: {
      title: "Version Odoo prise en charge",
      body: "Odoo 19. AgriWare Connector dépend de quatre modules de l'Odoo Community Association (OCA) — component, component_event, connector et queue_job — qui sont inclus dans le téléchargement de la marketplace Odoo Apps : aucune installation séparée n'est nécessaire pour une installation depuis la marketplace.",
    },
    architecture: {
      title: "Architecture d'intégration",
      body: "Chaque requête de cette intégration est initiée par le WMS externe ; Odoo n'appelle jamais le WMS. Toutes les données résident finalement dans la base PostgreSQL d'Odoo — AgriWare Connector n'ajoute aucun entrepôt de données séparé.",
      diagram: {
        wms: "WMS externe",
        api: "HTTPS + clé API",
        connector: "AgriWare Connector",
        odoo: "Odoo 19 Inventaire",
        db: "PostgreSQL",
      },
    },
    api: {
      title: "Capacités de l'API REST",
      body: "AgriWare Connector expose une API REST versionnée, enracinée à /agriware/api/v1. Toutes les réponses du contrôleur partagent une forme cohérente {\"status\": \"success\" | \"error\", ...}.",
      capabilities: [
        "GET /health — contrôle de santé public, aucune authentification requise",
        "GET /products — récupération de jusqu'à 100 produits ; POST /products et PATCH /products/{external_id} — création et mise à jour des produits",
        "GET /warehouses — récupération des entrepôts ; POST /warehouses et PATCH /warehouses/{external_id} — création et mise à jour des entrepôts",
        "GET /suppliers, POST /suppliers et PATCH /suppliers/{external_id} — récupération, création et mise à jour des fournisseurs",
        "GET /inventory — récupération des quantités de stock disponibles",
        "GET /lots, POST /lots et PATCH /lots/{external_id} — récupération, création et résolution des lots et numéros de série",
        "POST /inventory-adjustments — mise en attente d'un comptage d'inventaire initial pour révision humaine dans Odoo",
        "POST /receipts et /receipts/{id}/validate — création et validation des réceptions entrantes, y compris pour les produits suivis par lot ou numéro de série",
        "GET /receipts/{external_reference} — consultation du statut d'une réception par votre propre référence externe",
        "POST /dispatches et /dispatches/{id}/validate — création et validation des expéditions sortantes, y compris pour les produits suivis par lot ou numéro de série",
        "GET /dispatches/{external_reference} — consultation du statut d'une expédition par votre propre référence externe",
      ],
    },
    auth: {
      title: "Authentification et contrôle d'accès",
      body: "Chaque endpoint protégé requiert un en-tête Authorization: Bearer portant une véritable clé API Odoo. Les clés sont générées et gérées en libre-service, à l'intérieur d'Odoo, par les utilisateurs du groupe AgriWare Administrator — sans intervention d'un développeur. L'utilisateur sous-jacent de la clé authentifiée doit également appartenir au groupe AgriWare API User pour appeler l'API. Les clés API sont isolées par entreprise grâce à des règles d'enregistrement.",
    },
    operations: {
      title: "Opérations d'inventaire prises en charge",
      items: [
        "Lecture des données de produits, d'entrepôts, de fournisseurs et de stocks",
        "Création et mise à jour des produits, entrepôts et fournisseurs, identifiés par vos propres identifiants externes",
        "Configuration des correspondances d'unités de mesure pour les unités non fournies par défaut dans Odoo",
        "Création et résolution des lots et numéros de série pour les produits traçables",
        "Mise en attente des observations d'inventaire initial pour révision humaine — elles ne sont jamais appliquées automatiquement au stock réel ; un responsable d'inventaire doit les examiner et les appliquer manuellement depuis l'écran natif d'ajustement d'inventaire d'Odoo",
        "Création d'une réception entrante en brouillon, puis validation par rapport aux quantités reçues, y compris pour les produits suivis par lot ou numéro de série",
        "Création d'une expédition sortante en brouillon, puis validation par rapport aux quantités expédiées, y compris pour les produits suivis par lot ou numéro de série",
        "Consultation du statut d'une réception ou d'une expédition par votre propre référence externe",
        "Protection contre les transactions en double via un verrou consultatif PostgreSQL sur chaque référence externe",
      ],
    },
    limitations: {
      title: "Limitations actuelles",
      items: [
        "Pas de pagination sur les endpoints produits, entrepôts ou inventaire (plafonnés à 100 enregistrements)",
        "Pas de contrôle d'accès par entrepôt au sein d'une même entreprise",
        "Les réceptions et expéditions partielles ne sont pas prises en charge — les quantités doivent correspondre exactement",
        "Les imports d'inventaire initial sont mis en attente pour révision humaine — l'application d'un comptage validé au stock réel Odoo nécessite toujours une étape manuelle dans l'écran natif d'ajustement d'inventaire d'Odoo, par conception",
        "Aucune synchronisation automatique ou planifiée — chaque requête est initiée par le WMS externe",
        "Pas d'adaptateurs intégrés spécifiques à un WMS — il s'agit d'une seule API REST générique",
      ],
    },
    screenshots: {
      title: "Captures d'écran",
      items: [
        {
          src: "/images/screenshot_apps_listing.png",
          alt: "AgriWare Connector listé dans l'écran Apps d'Odoo",
          caption: "AgriWare Connector listé dans l'écran Apps d'Odoo.",
        },
        {
          src: "/images/screenshot_api_management.png",
          alt: "Écran API Management d'AgriWare Connector affichant une clé API en libre-service",
          caption:
            "L'écran API Management, où un utilisateur professionnel autorisé génère, consulte et révoque ses propres clés API.",
        },
        {
          src: "/images/screenshot_api_health.png",
          alt: "Réponse du contrôle de santé de l'API REST d'AgriWare Connector",
          caption: "Le endpoint de contrôle de santé de l'API REST, confirmé en ligne et fonctionnel.",
        },
      ],
    },
  },
  services: {
    title: "Services professionnels",
    intro:
      "Le logiciel d'AgriWare Connector est, et restera toujours, gratuit et open-source. Ces services payants optionnels sont réalisés par des personnes, pour les entreprises souhaitant un accompagnement pratique au-delà de la documentation.",
    freeNote:
      "Rien ci-dessous ne débloque une fonctionnalité par ailleurs restreinte — chaque capacité documentée de l'API REST est déjà gratuite. Ce sont des services, pas des paliers de licence logicielle.",
    packages: [
      {
        name: "1. Installation et configuration Odoo",
        description:
          "Installation d'AgriWare Connector et de ses dépendances OCA incluses sur votre instance Odoo 19, attribution des droits utilisateur, et génération de la première clé API.",
      },
      {
        name: "2. Intégration WMS de base",
        description:
          "Configuration de votre WMS existant face à l'API REST d'AgriWare Connector lorsqu'il parle déjà un protocole compatible, et validation de la connexion de bout en bout.",
      },
      {
        name: "3. Développement d'adaptateur WMS personnalisé",
        description:
          "Construction d'une couche de traduction entre le protocole natif de votre WMS et l'API REST d'AgriWare Connector, pour les WMS qui ne peuvent pas la parler directement.",
      },
      {
        name: "4. Personnalisation des flux d'inventaire",
        description:
          "Adaptation de la façon dont les réceptions et expéditions correspondent à votre processus opérationnel spécifique, dans les limites de ce que permet le flux de stock d'Odoo.",
      },
      {
        name: "5. Support technique et maintenance",
        description:
          "Assistance continue et dédiée, au-delà du support communautaire au mieux-effort, pour les entreprises souhaitant une continuité après la mise en production de leur intégration.",
      },
    ],
    optionalNote: "Chaque service ci-dessus est entièrement optionnel. Utiliser AgriWare Connector vous-même, gratuitement, reste pleinement pris en charge.",
    noPricingNote:
      "Les tarifs sont discutés au cas par cas selon le périmètre — aucune grille tarifaire n'est publiée ici.",
    cta: "Demander une assistance intégration",
  },
  documentation: {
    title: "Documentation",
    intro:
      "La documentation complète se trouve dans le dépôt GitHub du projet, aux côtés du code source.",
    links: [
      {
        label: "Guide d'installation",
        href: `${DOCS_BASE}/INSTALLATION.md`,
        description: "Instructions d'installation étape par étape, sans expérience de développement Odoo requise.",
        external: true,
      },
      {
        label: "Guide de démarrage rapide",
        href: `${DOCS_BASE}/QUICK_START.md`,
        description: "Le chemin le plus rapide à travers tout le flux de travail, avec un exemple minimal fonctionnel.",
        external: true,
      },
      {
        label: "Guide de démarrage rapide (français)",
        href: `${DOCS_BASE}/QUICK_START_FR.md`,
        description: "Traduction française du guide de démarrage rapide.",
        external: true,
      },
      {
        label: "Guide d'intégration WMS",
        href: `${DOCS_BASE}/WMS_INTEGRATION.md`,
        description: "Architecture, authentification, chaque endpoint avec exemples et gestion des erreurs.",
        external: true,
      },
      {
        label: "Référence API",
        href: `${DOCS_BASE}/API.md`,
        description: "La spécification technique complète, champ par champ, de chaque endpoint.",
        external: true,
      },
      {
        label: "Support client",
        href: `${DOCS_BASE}/SUPPORT.md`,
        description: "Comment signaler des problèmes d'installation/API, des bugs, et demander des fonctionnalités.",
        external: true,
      },
    ],
  },
  contact: {
    title: "Contact — Assistance intégration",
    intro:
      "Utilisez ce formulaire pour décrire vos besoins d'intégration. Les champs ci-dessous servent à évaluer la compatibilité technique avant toute proposition.",
    formDisabledTitle: "L'envoi du formulaire n'est pas encore connecté",
    formDisabledBody:
      "Ce formulaire valide votre saisie, mais son envoi n'est pas encore activé — aucun service d'envoi n'a encore été configuré pour ce site. La soumission n'enverra vos informations nulle part. En attendant, utilisez plutôt le canal de contact ci-dessous.",
    fields: {
      companyName: "Nom de l'entreprise",
      contactName: "Nom du contact",
      email: "Courriel professionnel",
      country: "Pays",
      existingErp: "ERP existant",
      existingWms: "WMS existant",
      requiredIntegration: "Intégration requise",
      projectDescription: "Description du projet",
    },
    submit: "Envoyer (pas encore disponible)",
    privacyTitle: "Confidentialité",
    privacyBody:
      "Ce formulaire ne stocke aucune donnée dans votre navigateur et ne transmet rien tant que l'envoi est désactivé. Une fois une méthode d'envoi réelle configurée, cette note sera mise à jour pour expliquer précisément ce qu'il advient des informations soumises.",
    alternateContact: "En attendant, consultez le guide de support client pour savoir comment contacter le projet sur GitHub.",
  },
};
