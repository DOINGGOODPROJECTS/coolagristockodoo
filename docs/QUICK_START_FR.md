# Guide de démarrage rapide

*Version française de [QUICK_START.md](QUICK_START.md). Les autres guides (installation détaillée,
intégration WMS, référence API) ne sont pour l'instant disponibles qu'en anglais — les liens
ci-dessous pointent vers ces documents anglais.*

Le chemin le plus rapide pour comprendre comment Cool Agristock s'articule. Pour le détail
complet, voir [INSTALLATION.md](INSTALLATION.md) (installation étape par étape) et
[WMS_INTEGRATION.md](WMS_INTEGRATION.md) (guide d'intégration complet pour développeurs).

## Le flux de travail de base

```text
INSTALLER COOL_AGRISTOCK CONNECTOR
          |
          v
ATTRIBUER LES DROITS UTILISATEUR
          |
          v
GÉNÉRER UNE CLÉ API
          |
          v
CONFIGURER LE WMS EXTERNE
          |
          v
TESTER LA CONNEXION API
          |
          v
ÉCHANGER LES DONNÉES D'ENTREPÔT
```

1. **Installer Cool Agristock** — depuis la marketplace Odoo Apps, sur votre instance Odoo 19.
   Le téléchargement inclut déjà ses dépendances OCA requises : il n'y a rien d'autre à récupérer.
   Voir [INSTALLATION.md](INSTALLATION.md#1-download-cool_agristock-connector-from-odoo-apps).
2. **Attribuer les droits utilisateur** — accordez le droit d'accès **Cool Agristock Administrator** à la
   personne qui gérera les clés API. Voir
   [INSTALLATION.md](INSTALLATION.md#4-assign-the-appropriate-user-permissions).
3. **Générer une clé API** — depuis **Cool Agristock → API Management → Generate API Key**, en
   choisissant une date d'expiration ou **Never Expires** (n'expire jamais). Voir
   [INSTALLATION.md](INSTALLATION.md#6-generate-an-api-key).
4. **Configurer votre WMS externe** — avec l'URL de base de votre instance Odoo
   (`https://VOTRE_URL_ODOO/cool_agristock/api/v1`) et la clé API, en utilisant l'authentification par
   jeton Bearer (Bearer token).
5. **Tester la connexion API** — vérifiez que le contrôle de santé (*health check*) et un appel
   authentifié fonctionnent tous les deux (exemple ci-dessous).
6. **Échanger les données d'entrepôt** — votre WMS appelle l'API REST pour lire les produits,
   entrepôts et stocks, et pour créer et valider les réceptions et expéditions. Voir
   [WMS_INTEGRATION.md](WMS_INTEGRATION.md) pour l'ensemble complet des opérations.

## Un exemple minimal : s'authentifier sur l'endpoint produits

En utilisant des valeurs d'exemple — remplacez-les par l'URL de votre propre instance et une clé
réellement générée (ne jamais enregistrer de vraies valeurs dans un dépôt de code) :

```bash
export ODOO_URL="https://VOTRE_URL_ODOO"
export API_KEY="VOTRE_CLE_API"

curl -s "$ODOO_URL/cool_agristock/api/v1/products" \
  -H "Authorization: Bearer $API_KEY"
```

Réponse attendue :

```json
{
  "status": "success",
  "count": 2,
  "products": [
    {"id": 14, "name": "Urea 50kg Bag", "default_code": "FERT-UREA-50", "barcode": "6161100000012", "active": true},
    {"id": 15, "name": "Maize Seed 25kg Bag", "default_code": "SEED-MAIZE-25", "barcode": "", "active": true}
  ]
}
```

Si vous obtenez une page HTML `401` au lieu de ce JSON, vérifiez le jeton Bearer — voir
[la section Dépannage d'INSTALLATION.md](INSTALLATION.md#troubleshooting).

## Recommandations de sécurité

- Conservez chaque clé générée comme un secret : stockez-la dans le gestionnaire de secrets de
  votre WMS, jamais dans un dépôt de code source ou un fichier de configuration en clair.
- Préférez une clé avec date d'expiration plutôt que **Never Expires**, sauf si votre intégration a
  réellement besoin d'une clé de longue durée.
- Révoquez immédiatement une clé si vous soupçonnez une fuite, puis générez-en une nouvelle.
- Déployez votre instance derrière HTTPS dans tout environnement au-delà du développement local —
  un jeton Bearer envoyé en clair (HTTP) est visible sur le réseau.

## Ce que Cool Agristock n'est pas

- Ce n'est pas un WMS en soi — c'est la couche d'intégration entre votre WMS existant et
  l'Inventaire Odoo.
- Il ne pousse pas de données vers votre WMS selon un calendrier — chaque échange est initié par
  votre WMS, qui appelle l'API REST.
- Il ne gère pas encore automatiquement les réceptions/expéditions partielles ni le suivi par
  lot/numéro de série — voir
  [les limitations connues de WMS_INTEGRATION.md](WMS_INTEGRATION.md#known-limitations).

## Étapes suivantes

- Guide d'installation complet : [INSTALLATION.md](INSTALLATION.md)
- Guide d'intégration complet pour développeurs : [WMS_INTEGRATION.md](WMS_INTEGRATION.md)
- Référence API complète : [API.md](API.md)
