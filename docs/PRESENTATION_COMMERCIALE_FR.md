# Cool Agristock — Présentation commerciale

*Document destiné aux agro-industries et aux intégrateurs Odoo intéressés par une connexion entre
leur WMS (système de gestion d'entrepôt) et Odoo 19. Toutes les affirmations ci-dessous reflètent
exactement les fonctionnalités documentées et vérifiées du module — aucune fonctionnalité non
implémentée n'y est annoncée.*

## 1. Que fait Cool Agristock ?

Cool Agristock est une application Odoo 19 gratuite et open-source qui permet à un système de
gestion d'entrepôt (WMS) externe compatible d'échanger des informations de produits, d'entrepôts et
de stocks avec Odoo Inventory, via une API REST documentée. Le WMS externe peut :

- consulter la liste des produits, des entrepôts et des stocks disponibles ;
- créer et valider des réceptions de marchandises (livraisons entrantes) ;
- créer et valider des expéditions (livraisons sortantes).

**Cool Agristock n'est pas lui-même un WMS.** Il ne gère ni le rayonnage, ni les circuits de
préparation, ni le matériel de lecture de codes-barres — c'est la couche d'intégration entre un WMS
existant et le module Inventaire d'Odoo.

## 2. Quelles entreprises peuvent en bénéficier ?

- Coopératives agricoles
- Distributeurs de produits agricoles
- Entreprises de transformation agroalimentaire
- Opérateurs d'entrepôts frigorifiques
- Entrepôts agricoles en général
- Exportateurs et importateurs
- Entreprises utilisant déjà Odoo mais dont le WMS n'est pas connecté
- Entreprises utilisant un ERP et un WMS distincts

**Condition essentielle :** l'entreprise doit déjà utiliser (ou prévoir d'utiliser) Odoo 19, et
disposer d'un WMS existant. **Cool Agristock ne remplace pas un WMS et ne se connecte pas
automatiquement à n'importe quel logiciel d'entrepôt** — le WMS doit pouvoir dialoguer avec l'API
REST documentée, ou faire l'objet d'une adaptation technique (voir point 6).

## 3. Quels problèmes de gestion d'entrepôt cela résout-il ?

- La double saisie manuelle des réceptions et expéditions, une fois dans le WMS, une fois dans
  Odoo — source d'erreurs et de perte de temps.
- Le manque de visibilité en temps quasi réel sur les stocks entre le système d'entrepôt et le
  système comptable/ERP.
- Les écarts de stock dus à des systèmes non synchronisés.

## 4. Comment cela s'intègre-t-il avec Odoo 19 ?

Le WMS externe appelle l'API REST de Cool Agristock (jamais l'inverse) :

```text
WMS externe  --(clé API, HTTPS)-->  Cool Agristock  --(ORM Odoo)-->  Odoo 19 Inventaire
```

Chaque échange est **initié par le WMS**, pas par Odoo. Il n'y a pas de synchronisation automatique
ou planifiée : le WMS appelle l'API quand il en a besoin.

## 5. Pourquoi l'application est-elle gratuite ?

Cool Agristock est publié sous licence open-source LGPL-3.0, sans frais de licence, sans
abonnement obligatoire, maintenant et pour toujours. Le code source est public sur GitHub. Une
entreprise disposant déjà des compétences techniques internes peut télécharger, installer et
connecter son propre WMS sans payer quoi que ce soit à Cool Agristock.

## 6. Quels services professionnels sont optionnels ?

Pour les entreprises qui souhaitent une assistance pratique plutôt que de tout faire elles-mêmes,
Cool Agristock, l'équipe à l'origine de Cool Agristock, propose séparément :

- Installation et configuration d'Odoo
- Intégration WMS de base (si le WMS parle déjà l'API documentée)
- Développement d'un adaptateur WMS personnalisé (si le WMS ne parle pas nativement l'API)
- Personnalisation des flux de gestion de stock
- Dépannage d'intégration API
- Formation technique
- Support et maintenance continue

Ces services sont **entièrement optionnels et payants, séparés du logiciel lui-même**, qui reste
gratuit quel que soit le choix de l'entreprise. Aucun tarif n'est publié ici — chaque demande est
évaluée individuellement (voir [PROFESSIONAL_SERVICES.md](PROFESSIONAL_SERVICES.md)).

## 7. Comment demander un accompagnement pour l'intégration ?

Toute entreprise intéressée peut contacter l'équipe par courriel à l'adresse
**team@agricarecentres.com**, en décrivant son WMS actuel et ses besoins. Pour une demande
d'intégration structurée, un questionnaire de qualification est disponible dans
[INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md) — il permet d'évaluer la compatibilité technique
du WMS avant de proposer un accompagnement. **Aucune compatibilité n'est garantie avant cette
évaluation.**

---

Pour plus de détails techniques, voir le [Guide de démarrage rapide](QUICK_START_FR.md) ou,
en anglais, la documentation complète : [README.md](../README.md).
