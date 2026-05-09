# Ymmo — plateforme immobilière

> Projet UF B2 — Ynov Informatique. Volet **Développement** d'une plateforme web complète pour Ymmo : siège à Aix-en-Provence + 12 agences. Achat / vente / estimation / pilotage du marché.

---

## Démarrage rapide

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python seed.py                  # peuple SQLite avec un jeu de démo (~120 biens)
python app.py                   # http://127.0.0.1:5000
```

### Comptes de démo

| Rôle  | Email             | Mot de passe   |
|-------|-------------------|----------------|
| Admin | `admin@ymmo.fr`   | `admin12345`   |
| Agent | `agent@ymmo.fr`   | `agent12345`   |
| Client| `client@ymmo.fr`  | `client12345`  |

### Tests

```bash
pytest        # 20 tests, ~12 s
```

---

## Ce qui est dans la boîte

### Côté visiteur
- Accueil éditorial avec recherche rapide en hero
- Catalogue paginé + filtres (mots-clés, ville, type, prix, surface, équipements) avec rail sticky en desktop
- Fiche bien (galerie type 1+4, caractéristiques, localisation, contact agence)
- Tableau de bord du marché : KPIs, prix moyens par ville, score d'opportunité, distribution, équipements
- Estimateur de prix (régression linéaire scikit-learn entraînée sur le portefeuille)
- Annuaire des 12 agences

### Côté client (compte)
- Favoris, demandes de visite, contact agence, suivi des transactions

### Côté agent
- CRUD biens (avec upload d'images), gestion des visites (confirmer / terminer / annuler), avancement transactions (offre → compromis → signature), KPIs personnels et réseau

### Côté admin
- Gestion utilisateurs (changement de rôle, désactivation), affectation aux agences, création d'agents

### API JSON (CSRF-exempt)
- `GET  /api/properties` — liste filtrée
- `GET  /api/dashboard`  — KPIs marché
- `POST /api/estimate`   — prédiction de prix

### Bonus
- **i18n** FR / EN avec Flask-Babel (cookie persistant 1 an)
- **Thème** clair / sombre avec préférence OS + override utilisateur (sans flash)
- **Accessibilité** : WCAG AA, focus visibles, ARIA, navigation clavier, `prefers-reduced-motion`
- Mobile-first, breakpoints 600 / 900 / 1100 px
- 100 % utilisable **sans JavaScript** (le JS améliore, n'est pas requis)

---

## Architecture

Architecture en couches (factory pattern, blueprints, séparation des responsabilités) :

```
ymmo/
├── app.py                      # entrée WSGI
├── config.py                   # configuration par environnement
├── seed.py                     # peuplement démo
├── babel.cfg                   # extraction i18n
├── ymmo/
│   ├── __init__.py             # application factory
│   ├── extensions.py           # SQLAlchemy, LoginManager, CSRFProtect, Babel
│   ├── decorators.py           # @role_required
│   ├── models/                 # entités SQLAlchemy + enums du domaine
│   ├── repositories/           # accès BDD + SQL avancé
│   ├── services/               # logique métier (auth, property, transaction, analytics)
│   ├── forms/                  # WTForms + validation
│   ├── analytics/              # data cleaning, indicateurs marché, modèle ML
│   ├── blueprints/             # routes HTTP : public, auth, client, agent, admin, api
│   ├── templates/              # Jinja2
│   ├── static/                 # CSS, JS, images, uploads
│   └── translations/           # fichiers .po / .mo
└── tests/                      # pytest
```

Les principes appliqués : **SOLID** (un module = une responsabilité, services et repositories injectables et testables, enums fermés sur les statuts du domaine), **DRY** (macros Jinja partagées, helpers SQL paramétrés), **KISS** (CSS vanilla, pas de framework JS).

### Stack

- Python 3.11+
- Flask 3 + Jinja2 + Flask-Login + Flask-WTF + Flask-Babel
- SQLAlchemy 2 (SQLite par défaut, PostgreSQL via `YMMO_DATABASE_URI`)
- pandas + numpy + scikit-learn (estimateur de prix)
- HTML5 / CSS3 vanilla, JS minimal en `defer`

### Modèle relationnel

```
agencies (1) ── (N) users [role=agent]
agencies (1) ── (N) properties
users    (1) ── (N) properties [agent_id]
users    (1) ── (N) favorites      ── (N) properties
users    (1) ── (N) visit_requests ── (1) properties
users    (1) ── (N) transactions   ── (1) properties
users    (1) ── (N) messages       ── (1) properties
properties (1) ─ (N) property_images
```

Forme normale 3NF, index sur `email`, `role`, `city`, `postal_code`, `price`, `surface`, `created_at`, `status`.

### Requêtes SQL avancées

Toutes les requêtes utilisateur passent par des **paramètres liés** pour bloquer l'injection.

`PropertyRepository.search` — recherche paginée multi-critères :

```sql
SELECT id FROM properties p
WHERE p.status IN (:status_0, ...)
  AND LOWER(p.title) LIKE :kw
  AND p.price BETWEEN :min_price AND :max_price
ORDER BY p.created_at DESC
LIMIT :limit OFFSET :offset;
```

`PropertyRepository.avg_price_per_city` — agrégation avec `HAVING` :

```sql
SELECT city, COUNT(*), AVG(price/surface), AVG(price), AVG(surface)
FROM properties
WHERE surface > 0 AND status IN ('available','sold','under_offer')
GROUP BY city HAVING COUNT(*) >= 1
ORDER BY AVG(price/surface) DESC LIMIT :limit;
```

`TransactionRepository.kpis` — panier moyen + durée moyenne du cycle dans une seule requête, avec `julianday()` et agrégations conditionnelles.

### Module analyse de données

- `build_property_dataframe()` — extraction SQL + nettoyage (typage, suppression des lignes invalides, calcul `price_per_sqm`)
- `MarketAnalysis` — équipements populaires, prix moyen par type, **score d'opportunité par ville** (signal demande − coût normalisés), distribution des prix
- `PricePredictor` — pipeline scikit-learn (`OneHotEncoder` + `LinearRegression`) ; le score R² s'affiche dans l'UI comme indicateur de confiance

### Sécurité

- Sessions HttpOnly + SameSite Lax (+ cookie sécurisé en prod)
- Mots de passe hachés (Werkzeug PBKDF2-SHA256)
- CSRF protégé sur tous les `POST` de formulaire (Flask-WTF) ; l'API JSON est exemptée explicitement
- Validation côté serveur (WTForms) + types stricts dans les services
- Vérification d'autorisation : `@role_required(...)` + contrôles métier (ex. `PropertyService._authorize_modify`)
- `MAX_CONTENT_LENGTH` 8 Mo, extensions d'image filtrées (`png/jpg/jpeg/webp`)

### Accessibilité, responsive, performance

- HTML5 sémantique + ARIA (`aria-label`, `aria-live`, `aria-current`, `role="banner|main|contentinfo|status"`)
- Skip-link, focus visible (2 px ≠ couleur de fond), contrastes ≥ 4.5:1
- Mode sombre via `prefers-color-scheme`, animations désactivées via `prefers-reduced-motion`
- Mobile-first, navigation hamburger sous 960 px
- Images : `loading="lazy"`, `aspect-ratio`, SVG placeholder
- Pas de framework front : ~30 lignes de JS, chargé en `defer`

---

## Déploiement

Variables d'environnement (cf. `.env.example`) :

- `YMMO_ENV=production`
- `YMMO_SECRET_KEY=...`
- `YMMO_DATABASE_URI=postgresql://...`

Lancement WSGI : `waitress-serve --port=8000 app:app` ou `gunicorn app:app`.

---

## Roadmap

- Recherche géolocalisée (lat/long déjà présents en base)
- Notifications email (visites, transactions)
- Authentification SSO d'entreprise (intégration Active Directory côté INFRA)
- Modèle ML plus riche (gradient boosting + features de marché externes)
- Internationalisation au-delà du FR / EN
