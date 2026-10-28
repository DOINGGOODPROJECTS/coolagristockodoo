# Matériel de prospection client

*Modèles à usage interne pour la prospection commerciale de Cool Agristock en Côte d'Ivoire.
**Aucun message ci-dessous n'a été envoyé** — ce sont des brouillons à adapter et à valider avant
tout envoi réel. Chaque modèle contient des champs entre crochets `[ ]` à compléter.*

## A. Courriel d'introduction pour les agro-industries

**Objet :** Connecter votre système d'entrepôt à Odoo — module gratuit et open-source

```text
Bonjour [Nom du contact],

Je me permets de vous contacter au sujet de Cool Agristock, une application Odoo 19 gratuite
et open-source qui permet de connecter un système de gestion d'entrepôt (WMS) existant à Odoo
Inventaire, via une API REST documentée.

Si votre entreprise utilise (ou envisage d'utiliser) Odoo 19 et dispose d'un système d'entrepôt
distinct, ce module peut réduire la double saisie entre les deux systèmes pour les réceptions et
expéditions de marchandises.

Quelques points clés :
- Le logiciel est entièrement gratuit (licence LGPL-3.0), sans frais caché.
- Il expose une API permettant de consulter produits, entrepôts et stocks, et de créer/valider
  des réceptions et expéditions.
- Votre WMS doit pouvoir dialoguer avec cette API (ou être adapté pour le faire) — ce n'est pas
  une compatibilité automatique avec n'importe quel logiciel.

Si cela vous intéresse, je serais heureux d'échanger brièvement sur votre système actuel pour
évaluer la compatibilité technique, sans engagement de votre part.

Cordialement,
[Nom]
Cool Agristock — équipe Cool Agristock
team@agricarecentres.com
```

## B. Courriel de partenariat pour les intégrateurs Odoo

**Objet :** Proposition de partenariat — module complémentaire pour vos clients agro-industriels

```text
Bonjour [Nom du contact],

En tant que partenaire Odoo [vérifié via odoo.com/partners — tier à confirmer avant envoi], vous
accompagnez probablement des clients dans les secteurs agricole, de la distribution ou de la
transformation alimentaire.

Cool Agristock est un module Odoo 19 gratuit et open-source que nous avons développé pour
connecter un WMS externe à Odoo Inventaire via une API REST. Il est complémentaire à votre travail
d'implémentation Odoo — nous ne proposons pas de services d'implémentation Odoo générale,
seulement l'intégration WMS spécifique.

Nous serions intéressés par une collaboration : si l'un de vos clients a besoin de connecter un
WMS existant à Odoo, nous pourrions intervenir sur cette partie spécifique, en coordination avec
votre équipe.

Seriez-vous disponible pour un court échange afin d'explorer si cela pourrait être pertinent pour
certains de vos clients ?

Cordialement,
[Nom]
Cool Agristock — équipe Cool Agristock
team@agricarecentres.com
```

## C. Message court LinkedIn

```text
Bonjour [Prénom], je travaille sur Cool Agristock, un module Odoo 19 gratuit et open-source
qui connecte un WMS existant à Odoo Inventaire via une API REST. Si votre entreprise (ou vos
clients) utilise Odoo et un système d'entrepôt séparé, ça pourrait réduire la double saisie entre
les deux. Ouvert à en discuter si ça vous intéresse ?
```

## D. Questionnaire de découverte client

À utiliser lors d'un premier échange (par téléphone, visioconférence ou courriel) pour qualifier un
prospect — correspond au questionnaire anglais dans
[INTEGRATION_SERVICES.md](INTEGRATION_SERVICES.md#customer-requirements-questionnaire) :

```markdown
**Nom et version du WMS utilisé**


**Environnement d'hébergement** (hébergement du WMS, et d'Odoo : auto-hébergé / Odoo.sh)


**Documentation API disponible pour votre WMS**
(lien, ou description générale — ne pas transmettre de documentation propriétaire que vous n'êtes
pas autorisé à partager)

**Méthode d'authentification de votre WMS**
(décrire de façon générale, par ex. « clé API dans un en-tête », « OAuth2 » — pas d'identifiants
réels)

**Opérations d'inventaire nécessaires**
(réception, expédition, consultation de stock, synchronisation produits — lesquelles des
opérations documentées de Cool Agristock vous sont utiles)

**Nombre d'entrepôts**


**Volume de transactions estimé**
(réceptions/expéditions par jour)

**Besoins de personnalisation**
(au-delà du comportement déjà documenté de l'API)

**Exigences de test**
(comment vous souhaitez valider l'intégration avant la mise en production)

**Exigences de déploiement**
(échéance souhaitée, qui effectue la bascule en production, contraintes d'indisponibilité)
```

## E. Message de relance pour prospects intéressés

**Objet :** Suite à notre échange — Cool Agristock

```text
Bonjour [Nom du contact],

Merci pour notre échange au sujet de Cool Agristock. Pour rappel, voici les points discutés :

- [Résumé en une ligne du besoin exprimé]
- [Système WMS/ERP actuel mentionné]

Prochaine étape proposée : [compléter le questionnaire de découverte / évaluation de compatibilité
technique / autre].

N'hésitez pas à me recontacter si vous avez des questions entre-temps.

Cordialement,
[Nom]
Cool Agristock — équipe Cool Agristock
team@agricarecentres.com
```

## Rappels importants pour toute utilisation de ces modèles

- Ne jamais inclure de promesse de performance non vérifiée (ex. : gains de temps chiffrés,
  réduction d'erreurs en pourcentage) — aucune de ces données n'existe actuellement.
- Ne jamais affirmer qu'un WMS est compatible avant l'évaluation technique.
- Ne jamais inclure de prix ferme avant un appel de découverte réel (voir
  [docs/COMMERCIAL_STRATEGY.md](COMMERCIAL_STRATEGY.md), section 5 : les fourchettes de prix sont
  des estimations de planification, pas des tarifs validés).
