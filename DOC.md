# Ymmo — documentation technique (volet DEV)

> Projet UF B2 INFRA & DEV — Ynov Informatique
> Cette documentation couvre **uniquement la partie développement** : application web complète permettant à Ymmo (siège d'Aix-en-Provence + 12 agences) de centraliser ses opérations immobilières et d'analyser son marché.

---

## Sommaire

1. [Présentation fonctionnelle](#1-présentation-fonctionnelle)
2. [Stack technique](#2-stack-technique)
3. [Architecture](#3-architecture)
4. [Mise en route](#4-mise-en-route)
5. [Modèle de données](#5-modèle-de-données)
6. [Fonctionnalités par rôle](#6-fonctionnalités-par-rôle)
7. [Module d'analyse de données et ML](#7-module-danalyse-de-données-et-ml)
8. [Requêtes SQL avancées](#8-requêtes-sql-avancées)
9. [Sécurité](#9-sécurité)
10. [API JSON](#10-api-json)
11. [Internationalisation et thème](#11-internationalisation-et-thème)
12. [Accessibilité et performance](#12-accessibilité-et-performance)
13. [Tests](#13-tests)
14. [Déploiement](#14-déploiement)
15. [Choix techniques et justifications](#15-choix-techniques-et-justifications)
16. [Roadmap d'évolution](#16-roadmap-dévolution)

---

## 1. Présentation fonctionnelle

### 1.1 Acteurs et rôles

| Rôle | Permissions principales |
|------|-------------------------|
| **Visiteur** | Consulte le catalogue, l'estimation, le tableau de bord du marché, les agences. Aucun compte requis. |
| **Client** | + Favoris, demandes de visite, messages aux agences, suivi de ses transactions, alertes (recherches sauvegardées). |
| **Agent immobilier** | Gestion CRUD de ses biens (avec photos), traitement des visites, suivi et progression des transactions, KPI personnels et réseau, calendrier hebdo, action groupée, export CSV. |
| **Administrateur** | Gestion des utilisateurs (rôles, désactivation, affectation aux agences), création d'agents, ranking des agents, exports CSV, supervision globale. |

### 1.2 Parcours utilisateurs

**Côté client (brief Ymmo §1) :**
- consulter les biens disponibles → recherche multi-critères paginée
- accéder aux fiches détaillées (description, prix, localisation, photos, caractéristiques, carte interactive)
- contacter une agence (formulaire de message)
- effectuer des demandes d'information ou de visites
- suivre l'avancement de ses démarches (favoris / visites / transactions avec timeline)
- recevoir des alertes sur de nouveaux biens correspondant à des critères sauvegardés
- comparer 2 à 4 biens côte à côte

**Côté agences / commerciaux :**
- ajouter et modifier des biens immobiliers (avec upload de photos)
- gérer les dossiers clients (visites, messages)
- suivre les transactions (offre → compromis → signature)
- consulter les tableaux de bord et statistiques (KPI réseau, CA mensuel, anomalies)
- voir quels clients ont mis leurs biens en favori
- vue calendrier hebdomadaire des visites
- action groupée (changement de statut sur plusieurs biens)
- export CSV de leur portefeuille

**Analyse de données et IA :**
- analyse du marché immobilier (prix moyens, distribution, équipements populaires)
- identification des tendances par ville et par type
- statistiques et indicateurs (panier moyen, durée du cycle, vélocité de vente)
- aide à la décision : score d'opportunité par zone, ranking des agents, anomalies
- prédictions : prix d'un bien, délai estimé de vente

**Sécurité et accès :**
- trois rôles, vérifiés via décorateur `@role_required`
- mots de passe hachés (Werkzeug PBKDF2-SHA256), sessions HttpOnly + SameSite Lax
- protection CSRF sur tous les formulaires (Flask-WTF)
- rate-limiting sur les endpoints d'authentification (anti-bruteforce)
- architecture en couches (présentation → service → repository → modèle)

### 1.3 Pages publiques principales

| URL | Description |
|-----|-------------|
| `/` | Accueil avec biens populaires, tendances, recherche rapide |
| `/biens` | Liste filtrée + paginée avec rail de filtres sticky |
| `/biens/<id>` | Fiche détaillée avec galerie, carte Leaflet, prédiction de délai de vente |
| `/comparer` | Comparaison côte à côte (max 4 biens) |
| `/marche` | Tableau de bord du marché (CA mensuel, KPI, top zones, vélocité, distribution) |
| `/estimer` | Estimateur de prix par régression linéaire |
| `/agences` | Annuaire du réseau |
| `/auth/connexion`, `/auth/inscription`, `/auth/deconnexion` | Authentification |
| `/espace-client/*`, `/espace-agent/*`, `/admin/*` | Espaces privés selon le rôle |
| `/api/*` | API JSON (properties, dashboard, estimate, alerts, health) |

---

## 2. Stack technique

| Couche | Technologie |
|--------|-------------|
| Langage | Python 3.11+ |
| Framework web | Flask 3 (factory pattern, blueprints) |
| ORM | SQLAlchemy 2 + Flask-SQLAlchemy 3 |
| Auth | Flask-Login |
| Forms / CSRF | Flask-WTF + WTForms |
| i18n | Flask-Babel 4 (FR / EN) |
| Rate-limiting | Flask-Limiter |
| Migrations | Flask-Migrate (Alembic) |
| Données | pandas + numpy |
| Machine Learning | scikit-learn (LinearRegression + OneHotEncoder pipeline) |
| Frontend | HTML5 / CSS3 vanilla, JS minimal, pas de framework |
| Carte | Leaflet.js (CDN, OpenStreetMap, sans clé API) |
| Polices | Fraunces (serif) + Inter + JetBrains Mono via Google Fonts |
| BDD par défaut | SQLite (dev) — compatible PostgreSQL via `YMMO_DATABASE_URI` |
| Tests | pytest |

---

## 3. Architecture

### 3.1 Structure des dossiers

```
ymmo/
├── app.py                      Point d'entrée WSGI
├── config.py                   Configuration par environnement (dev/test/prod)
├── seed.py                     Peuplement démo (drop + create + insert)
├── babel.cfg                   Config extraction i18n
├── requirements.txt
├── pytest.ini
├── README.md / DOC.md          Documentation
├── .env.example                Variables d'environnement
├── .gitignore
│
├── ymmo/                       Package principal
│   ├── __init__.py             Application factory
│   ├── _time.py                Helper utcnow() (remplace datetime.utcnow déprécié)
│   ├── extensions.py           Instances singletons (db, login, csrf, babel, limiter, migrate)
│   ├── decorators.py           @role_required
│   ├── models/                 Entités SQLAlchemy + enums
│   │   ├── agency.py
│   │   ├── favorite.py
│   │   ├── message.py
│   │   ├── property.py
│   │   ├── saved_search.py
│   │   ├── transaction.py
│   │   ├── user.py
│   │   └── visit_request.py
│   ├── repositories/           Accès BDD (SQL textuel + ORM)
│   │   ├── agency_repository.py
│   │   ├── property_repository.py
│   │   ├── transaction_repository.py
│   │   └── user_repository.py
│   ├── services/               Logique métier (réutilisable hors HTTP)
│   │   ├── analytics_service.py
│   │   ├── auth_service.py
│   │   ├── property_service.py
│   │   ├── saved_search_service.py
│   │   └── transaction_service.py
│   ├── analytics/              Pandas + scikit-learn
│   │   ├── market_analysis.py  Indicateurs, anomalies, ranking, tendance
│   │   └── price_predictor.py  Modèle ML
│   ├── forms/                  WTForms + validation
│   │   ├── auth_forms.py
│   │   └── property_forms.py
│   ├── blueprints/             Routes HTTP par contexte
│   │   ├── public.py
│   │   ├── auth.py
│   │   ├── client.py
│   │   ├── agent.py
│   │   ├── admin.py
│   │   └── api.py
│   ├── templates/              Jinja2 (HTML5 sémantique)
│   │   ├── base.html           Layout, topbar, footer
│   │   ├── _macros.html        Macros (cartes, pagination, charts SVG)
│   │   ├── public/             home, list, detail, market, estimate, agencies, compare
│   │   ├── auth/               login, register
│   │   ├── client/             dashboard, alerts, contact, visit_request
│   │   ├── agent/              dashboard, calendar, property_form, property_favorites
│   │   ├── admin/              dashboard
│   │   └── errors/             403, 404, 429, 500
│   ├── static/
│   │   ├── css/main.css        Une seule feuille de style (~1150 lignes)
│   │   ├── js/main.js          Comportements progressifs
│   │   ├── js/compare.js       Comparateur via sessionStorage
│   │   ├── images/             favicon + placeholder
│   │   └── uploads/            Photos des biens (générées au runtime)
│   └── translations/           Catalogues FR/EN (.po + .mo)
│
└── tests/                      pytest
    ├── conftest.py
    ├── test_analytics.py
    ├── test_auth.py
    ├── test_pages.py
    └── test_property_search.py
```

### 3.2 Pattern factory

```python
# ymmo/__init__.py
def create_app(config_class=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())
    db.init_app(app); login_manager.init_app(app); ...
    app.extensions["analytics"] = AnalyticsService()  # singleton partagé
    register_blueprints(app); register_error_handlers(app); ...
    return app
```

**Pourquoi factory** : permet de créer plusieurs instances (dev, tests in-memory, prod) avec des configurations différentes sans état global, et d'éviter les imports circulaires entre modèles et extensions.

### 3.3 Architecture en couches

```
┌──────────────────────────────────────┐
│ Templates Jinja2 + CSS + JS          │  Présentation
└──────────────────────────────────────┘
              ▲
┌──────────────────────────────────────┐
│ Blueprints (public, auth, agent, …)  │  HTTP
└──────────────────────────────────────┘
              ▲
┌──────────────────────────────────────┐
│ Services (PropertyService, …)        │  Logique métier
└──────────────────────────────────────┘
              ▲
┌──────────────────────────────────────┐
│ Repositories (PropertyRepository, …) │  Accès BDD
└──────────────────────────────────────┘
              ▲
┌──────────────────────────────────────┐
│ Modèles SQLAlchemy + enums           │  Domaine
└──────────────────────────────────────┘
```

**Bénéfices :**
- chaque couche a une responsabilité unique (SOLID — SRP)
- les services peuvent être appelés depuis un blueprint web, une commande CLI ou un test sans modification
- les blueprints n'écrivent jamais de SQL directement
- les tests unitaires peuvent piloter directement les services en court-circuitant HTTP

### 3.4 Principes appliqués

- **SOLID :** un module = une responsabilité ; services et repositories injectables et testables ; enums fermés sur les statuts du domaine (Open/Closed)
- **DRY :** macros Jinja partagées (`property_card`, `pagination`, `line_chart`, `render_field`) ; helpers SQL paramétrés ; helpers temps centralisés
- **KISS :** pas de framework JS (vanilla, ~120 lignes au total) ; CSS unique ; site 100 % utilisable sans JavaScript

---

## 4. Mise en route

### 4.1 Prérequis
- Python ≥ 3.11
- pip

### 4.2 Installation

```bash
git clone https://github.com/Twifooo/ymmo.git
cd ymmo
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python seed.py                  # peuple SQLite avec ~120 biens de démo
python app.py                   # http://127.0.0.1:5000
```

### 4.3 Comptes de démonstration

| Rôle  | Email             | Mot de passe   |
|-------|-------------------|----------------|
| Admin | `admin@ymmo.fr`   | `admin12345`   |
| Agent | `agent@ymmo.fr`   | `agent12345`   |
| Client| `client@ymmo.fr`  | `client12345`  |

### 4.4 Variables d'environnement

Fichier `.env` (cf. `.env.example`) :

```
YMMO_ENV=development              # development | testing | production
YMMO_SECRET_KEY=changez-moi
# YMMO_DATABASE_URI=postgresql://user:pass@localhost/ymmo
```

`load_dotenv()` est appelé dans `app.py` et `seed.py` **avant** l'import de `config.py` (sinon les valeurs par défaut sont figées à l'import).

---

## 5. Modèle de données

### 5.1 Diagramme relationnel

```
agencies (1) ── (N) users [role=agent]
agencies (1) ── (N) properties
users    (1) ── (N) properties [agent_id]
users    (1) ── (N) favorites      ── (N) properties
users    (1) ── (N) visit_requests ── (1) properties
users    (1) ── (N) transactions   ── (1) properties [+ buyer_id, agent_id]
users    (1) ── (N) messages       ── (1) properties
users    (1) ── (N) saved_searches
properties (1) ─ (N) property_images
```

### 5.2 Tables et clés

| Table | Colonnes clés | Index |
|-------|----------------|-------|
| `users` | id, email (unique), role, agency_id, password_hash | email, role |
| `agencies` | id, name (unique), city, is_headquarters | city |
| `properties` | id, type, status, price, surface, city, latitude, longitude, agent_id, agency_id | type, status, price, surface, city, postal_code, created_at |
| `property_images` | id, property_id, url, alt_text, position | property_id |
| `favorites` | (user_id, property_id) UNIQUE | user_id, property_id |
| `visit_requests` | id, property_id, client_id, status, preferred_date | property_id, status |
| `transactions` | id, property_id, buyer_id, agent_id, status, offer_amount, final_amount, dates | status |
| `messages` | id, sender_id, recipient_id, property_id, sent_at | sender_id, recipient_id, sent_at |
| `saved_searches` | id, user_id, label, city, property_type, max_price, min_surface, last_seen_at | user_id |

Forme normale **3NF** : aucune redondance ; les enums sont stockés en valeurs de colonne (`'apartment'`, `'sold'`, etc.) plutôt qu'en sous-tables, pour rester compatible avec les requêtes SQL natives.

### 5.3 POO du domaine

Toutes les entités SQLAlchemy ont :

- des **enums** fermés (`UserRole`, `PropertyType`, `PropertyStatus`, `TransactionStatus`, `VisitStatus`) avec une property `.label` traduite via gettext
- des **propriétés calculées** (`User.full_name`, `Property.price_per_sqm`, `Property.main_image_url`)
- des **méthodes métier** (`User.set_password`, `User.has_role`, `SavedSearch.matches_query`)

```python
# ymmo/models/property.py — extrait
class PropertyType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    LAND = "land"
    COMMERCIAL = "commercial"
    OFFICE = "office"

    @property
    def label(self) -> str:
        return {PropertyType.APARTMENT: _("Appartement"), ...}[self]
```

Les colonnes `db.Column(db.Enum(...))` utilisent `values_callable=lambda x: [e.value for e in x]` pour stocker les **valeurs** (`'apartment'`) et non les **noms** (`'APARTMENT'`) — sinon les requêtes SQL natives `WHERE type = 'apartment'` ne matcheraient rien.

---

## 6. Fonctionnalités par rôle

### 6.1 Visiteur (anonyme)

- Catalogue paginé (12 biens / page) avec filtres : mots-clés, ville, type, prix min/max, surface min, pièces min, parking, jardin
- Tri : récent / prix asc/desc / surface desc / popularité
- Fiche bien complète : description, caractéristiques, galerie type Airbnb (1+4), carte Leaflet, **prédiction du délai de vente**
- Bouton "⊕ Comparer" sur les cartes (sessionStorage)
- Tableau de bord du marché public
- Estimateur de prix
- Annuaire des agences

### 6.2 Client connecté

Tout ce qui précède **plus** :

- ♥ Favoris (toggle depuis la fiche)
- Demande de visite (date souhaitée + message)
- Contact d'une agence (subject + body)
- Tableau de bord personnel :
  - mes recherches sauvegardées (badge "X nouveaux" depuis la dernière visite)
  - mes favoris en cartes
  - mes demandes de visite (statut)
  - **timeline d'avancement** des transactions (Offre → Compromis → Signature)
- Page `/alertes` : CRUD des recherches sauvegardées avec compteur live de matches

### 6.3 Agent

- Tableau de bord avec :
  - KPI : nb de biens, visites en attente, ventes signées réseau, panier moyen, **anomalies** (badge ⚠ si bien hors marché)
  - **Courbe SVG du CA mensuel signé** (sur l'année en cours)
  - Portefeuille **paginé** (10 / page) avec recherche par titre/ville
  - Action groupée : checkboxes + dropdown statut → mise à jour bulk
  - Lien vers les **clients ayant mis chaque bien en favori**
  - Tableau des demandes de visite (Confirmer / Terminée / Annuler)
  - Tableau des transactions avec progression (Compromis / Signer / Annuler)
- **Calendrier hebdomadaire** des visites confirmées (CSS Grid pure, navigation ± semaine)
- CRUD biens avec upload multi-images
  - rejets visibles (format invalide, fichier > 4 Mo) → flash UI
  - alt-text auto-généré et **sanitisé** (anti-XSS)
- Export CSV de son portefeuille

### 6.4 Administrateur

- KPI globaux : nb d'utilisateurs, agences, transactions, signées
- **Ranking des agents** (ventes signées DESC + panier moyen DESC + cycle ASC)
- Liste utilisateurs paginée avec :
  - **recherche** par nom/email
  - **filtre** par rôle
  - changement de rôle inline (auto-submit)
  - changement d'agence inline (auto-submit)
  - activation/désactivation
- Création directe d'un compte agent (avec affectation d'agence)
- Aperçu marché (top villes par prix au m²)
- Exports CSV : transactions du réseau + biens

---

## 7. Module d'analyse de données et ML

Conformément au programme B2 ("Analyse et manipulation de données en Python"), le module `ymmo/analytics/` est isolé du reste de l'app et exporte des fonctions consommables aussi bien depuis l'UI que via l'API JSON.

### 7.1 Pipeline

```
PropertyRepository.all_for_dataframe()       # SQL natif joint avec agencies
        ▼
build_property_dataframe(rows)               # nettoyage : typage strict,
                                             # drop des lignes invalides,
                                             # calcul price_per_sqm
        ▼
MarketAnalysis(df).<method>()                # agrégations / indicateurs
```

### 7.2 `MarketAnalysis` — méthodes

| Méthode | Sortie | Usage |
|---------|--------|-------|
| `popular_features()` | `{has_parking: 62.5, has_garden: 18.3, has_balcony: 24.1}` | KPIs marché |
| `average_price_per_type()` | `[{type: 'apartment', count, avg_price, avg_price_sqm, avg_surface}, ...]` | Cartes "Prix par type" |
| `best_zones_to_invest(top=5)` | `[{city, count, avg_price, avg_price_sqm, avg_views, opportunity_score}]` | Tableau "Zones à investir" |
| `price_distribution(bins=10)` | `[{min, max, count}, ...]` | Histogramme |
| `price_trend(months=6, top_cities=5)` | `{labels: [...mois...], series: {city: [...valeurs...]}}` | Line-chart SVG |
| `anomalies(sigma=2.0)` | Liste des biens dont le prix au m² s'écarte de plus de 2σ | Badge ⚠ |

### 7.3 Helpers indépendants

- `agent_ranking(transactions, top=10)` — classement des agents
- `monthly_revenue_chart(rows)` — 12 points (jan→déc) prêts pour line-chart
- `sales_velocity(transactions)` — durée moyenne offre→signature par type
- `trending_properties(rows, days=30, top=5)` — biens récents les plus vus

### 7.4 `PricePredictor` — estimation de prix

Pipeline scikit-learn :

```python
ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["type", "city"]),
], remainder="passthrough")  # surface, rooms, bedrooms, bathrooms, has_parking,
                             # has_garden, has_balcony passent en numérique
↓
LinearRegression()
```

- entraîné à la demande sur le portefeuille complet (cache une fois entraîné)
- `score` = R² affiché à l'utilisateur comme **indicateur de confiance** (R² ≈ 0.83 sur le jeu de seed)
- `reset_predictor()` invalidé après chaque CRUD bien pour forcer le réentraînement

### 7.5 Estimation du délai de vente (`estimate_days_to_sell`)

Heuristique combinant deux signaux :

```python
base = sales_velocity[prop.type]                         # moyenne par type
delta = (prop.price/sqm - market_avg_for_city_type) / market_avg
coeff = clamp(1 + 3*delta, 0.4, 2.5)                     # +10% → +30% lent
days  = max(7, base * coeff)
```

Affiché sur la fiche bien avec un tag indiquant l'écart vs marché local.

### 7.6 Détection d'anomalies

```python
grouped = df.groupby(["city", "type"])["price_per_sqm"].agg(["mean", "std"])
merged  = df.merge(grouped, on=["city","type"])
merged["zscore"] = (merged["price_per_sqm"] - merged["mean"]) / merged["std"]
flagged = merged[abs(merged["zscore"]) >= 2.0]
```

Le tableau de bord agent affiche un badge ⚠ et un KPI dédié si le bien dépasse 2σ vs la moyenne ville+type. La méthode `anomalies_for_agent()` filtre ensuite les IDs sur le portefeuille de l'agent (pas de fuite cross-agence).

---

## 8. Requêtes SQL avancées

Toutes les requêtes utilisateur passent par des **paramètres liés** (`text()` + `{"key": value}`) — aucune concaténation de chaîne.

### 8.1 Recherche multi-critères paginée

```python
# PropertyRepository.search
where_sql  = "WHERE p.status IN (...) AND LOWER(p.title) LIKE :kw AND p.price BETWEEN :min AND :max"
order_sql  = "p.created_at DESC"   # whitelist de colonnes
ids_sql    = text(f"SELECT p.id FROM properties p {where_sql} ORDER BY {order_sql} LIMIT :limit OFFSET :offset")
```

Tri whitelisté dans un `dict SORTS`, pas de injection possible. Le tri `popular` mappe vers `views_count DESC`, etc.

### 8.2 Agrégation `GROUP BY ... HAVING`

```sql
-- avg_price_per_city
SELECT city, COUNT(*), AVG(price/surface), AVG(price), AVG(surface)
FROM properties
WHERE surface > 0 AND status IN ('available','sold','under_offer')
GROUP BY city
HAVING COUNT(*) >= 1
ORDER BY AVG(price/surface) DESC
LIMIT :limit;
```

### 8.3 KPI multi-mesures en une requête

```sql
-- TransactionRepository.kpis
SELECT
    COUNT(*)                                                AS total_count,
    SUM(CASE WHEN status='signed'    THEN 1 ELSE 0 END)     AS signed_count,
    ROUND(AVG(CASE WHEN status='signed' THEN final_amount END), 2) AS avg_basket,
    ROUND(AVG(CASE WHEN status='signed' THEN
        CAST((julianday(signed_date) - julianday(offer_date)) AS INTEGER)
    END), 1) AS avg_cycle_days
FROM transactions;
```

`julianday()` (SQLite) est porté en `EXTRACT(EPOCH FROM …)/86400` côté Postgres si on migre.

### 8.4 Mise à jour groupée avec sécurité

```python
# PropertyRepository.bulk_update_status
ph = ",".join(f":id_{i}" for i in range(len(ids)))   # bind dynamique
clause = f"UPDATE properties SET status = :st WHERE id IN ({ph})"
if agent_id:
    clause += " AND agent_id = :aid"   # un agent ne peut toucher qu'à ses biens
```

### 8.5 Export joint pour analyse

```sql
-- TransactionRepository.all_for_dataframe : alimente pandas
SELECT t.id, t.status, t.offer_amount, t.final_amount,
       t.offer_date, t.compromise_date, t.signed_date,
       t.agent_id, (u.first_name||' '||u.last_name) AS agent_name,
       p.type AS property_type, p.city AS property_city
FROM transactions t
JOIN users u      ON u.id = t.agent_id
JOIN properties p ON p.id = t.property_id;
```

---

## 9. Sécurité

### 9.1 Authentification

- mots de passe **PBKDF2-SHA256** via `werkzeug.security.generate_password_hash`
- minimum 8 caractères validé côté serveur
- email normalisé en lowercase + trim avant comparaison

### 9.2 Sessions

- cookies **HttpOnly** + **SameSite Lax**
- `SESSION_COOKIE_SECURE = True` en `ProductionConfig` (HTTPS only)
- `PERMANENT_SESSION_LIFETIME = 8h`

### 9.3 CSRF

- `Flask-WTF CSRFProtect` actif sur tous les `POST` de formulaire
- chaque formulaire inclut `{{ form.csrf_token }}` (ou `<input name="csrf_token" value="{{ csrf_token() }}">` pour les mini-formulaires)
- **API JSON exemptée explicitement** via `csrf.exempt(api_bp)` (l'API utilise des tokens d'API en prod)

### 9.4 Rate-limiting (Flask-Limiter)

```python
@auth_bp.route("/connexion", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    ...
```

- 5 tentatives de connexion / minute / IP
- 3 inscriptions / minute / IP
- limite globale par défaut : 1000 req / heure / IP
- réponse 429 + page d'erreur dédiée
- headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` exposés

### 9.5 Autorisation

- décorateur `@role_required(UserRole.AGENT, UserRole.ADMIN)` sur les blueprints sensibles
- contrôles métier additionnels (`PropertyService._authorize_modify` : un agent ne modifie que ses biens)
- `bulk_update_status` filtre côté SQL par `agent_id` si l'acteur n'est pas admin

### 9.6 Upload de fichiers

- `MAX_CONTENT_LENGTH = 8 MB` (Flask)
- limite individuelle : 4 MB par image
- extensions whitelistées : `png / jpg / jpeg / webp` (vérifiées **après** `secure_filename`)
- nom de fichier hashé (`secrets.token_hex(8)_<original>`) pour éviter les collisions

### 9.7 XSS

- Jinja2 échappe par défaut (`{{ var }}` → HTML escape)
- alt-text des photos passe par `markupsafe.escape(prop.title)[:200]` avant insertion BDD (le titre est user-controlled)
- pas de `|safe` ni de `Markup(...)` dans les templates

### 9.8 SQL injection

- 100 % des paramètres utilisateur passent par `text(sql).bindparams(...)` ou via l'ORM
- les colonnes de tri sont whitelistées dans `PropertyRepository.SORTS`

---

## 10. API JSON

Préfixe : `/api`. CSRF exempté. Headers REST standards exposés.

| Endpoint | Méthode | Description | Headers |
|----------|---------|-------------|---------|
| `/api/health` | GET | Sonde déploiement (status, version, uptime, db) | — |
| `/api/properties` | GET | Recherche paginée (mêmes critères que `/biens`) | `X-Total-Count`, `X-Page`, `X-Per-Page`, `X-RateLimit-*` |
| `/api/dashboard` | GET | Tableau de bord complet (KPI + charts data) | — |
| `/api/estimate` | POST | Prédiction de prix (`{type, city, surface, rooms, ...}`) | — |
| `/api/alerts` | GET | Compteur d'alertes pour le client connecté | login requis |

### 10.1 Exemple `/api/health`

```json
GET /api/health
HTTP/1.1 200 OK

{
  "status": "ok",
  "version": "1.0.0",
  "uptime_s": 1234.5,
  "database": "ok"
}
```

### 10.2 Exemple `/api/properties`

```
GET /api/properties?city=Lyon&type=apartment&max_price=400000&per_page=3

HTTP/1.1 200 OK
X-Total-Count: 14
X-Page: 1
X-Per-Page: 3
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999

{ "total": 14, "page": 1, "per_page": 3, "items": [...] }
```

### 10.3 Exemple `/api/estimate`

```bash
curl -X POST http://127.0.0.1:5000/api/estimate \
     -H "Content-Type: application/json" \
     -d '{"type":"apartment","city":"Lyon","surface":60,"rooms":3,
          "bedrooms":2,"bathrooms":1,
          "has_parking":true,"has_garden":false,"has_balcony":true}'
```
```json
{
  "predicted_price": 418259.34,
  "price_per_sqm": 6970.99,
  "confidence": 0.831,
  "model": "LinearRegression + OneHotEncoder"
}
```

---

## 11. Internationalisation et thème

### 11.1 i18n FR / EN (Flask-Babel)

- 385 entrées traduites (UI + enums du domaine)
- sélecteur de locale : cookie `ymmo_lang` (1 an) > `Accept-Language` > FR
- macros et templates wrappés en `_()` / `ngettext()`
- switcher FR/EN dans la topbar (formulaire POST `/lang`)

Workflow d'extraction :

```bash
# Extraire les chaînes de tous les .py et .html
python -m babel.messages.frontend extract -F babel.cfg -o messages.pot .

# Mettre à jour le catalogue EN (préserve les traductions existantes)
python -m babel.messages.frontend update -i messages.pot -d ymmo/translations -l en

# Compiler en .mo (format binaire utilisé au runtime)
python -m babel.messages.frontend compile -d ymmo/translations
```

### 11.2 Thème clair / sombre

- détection auto via `@media (prefers-color-scheme: dark)`
- override utilisateur dans `localStorage` (`ymmo-theme: 'light' | 'dark'`)
- script anti-flash dans le `<head>` : applique `data-theme` **avant** le rendu
- bouton dans la topbar (toggle ◐/◑ animé)

---

## 12. Accessibilité et performance

- HTML5 sémantique : `<main>`, `<nav>`, `<aside>`, `<article>`, `<address>`
- ARIA : `aria-label`, `aria-live`, `aria-current`, `role="banner|main|contentinfo|status"`
- Skip-link "Aller au contenu principal" (visible au focus)
- Focus visible 2 px avec une couleur contrastée (`outline: 2px solid var(--brick)`)
- Contrastes ≥ 4.5:1 (WCAG AA) vérifiés sur toutes les couleurs de texte
- Mode sombre via `prefers-color-scheme`, animations désactivées via `prefers-reduced-motion`
- Mobile-first, navigation hamburger sous 960 px
- Images : `loading="lazy"`, `aspect-ratio`, SVG placeholder
- JS chargé en `defer`, ~150 lignes au total (main + compare)
- CSS unique d'environ 30 ko, compatible HTTP cache
- Site **utilisable sans JavaScript** (le JS améliore, n'est pas requis)
- Charts SVG faits main, pas de Chart.js / D3 (zéro dépendance frontend)
- Carte Leaflet chargée **uniquement** sur la fiche bien (pas sur les autres pages)

---

## 13. Tests

```bash
pytest                    # 20 tests, ~12s
```

| Fichier | Couverture |
|---------|------------|
| `test_auth.py` | inscription, connexion, mot de passe court rejeté, doublon email rejeté |
| `test_property_search.py` | recherche multi-critères, filtre par ville, filtre par type, agrégation `avg_price_per_city` |
| `test_analytics.py` | nettoyage DataFrame, calcul KPI, ranking agents, prédiction prix |
| `test_pages.py` | `/`, `/biens`, `/biens/<id>`, `/marche`, `/estimer`, `/agences`, login redirect |

Configuration pytest : `TestingConfig` avec SQLite in-memory, CSRF désactivé, Flask-Limiter désactivé (sinon faux 429).

---

## 14. Déploiement

### 14.1 WSGI

```bash
# Linux / macOS
gunicorn 'app:app' --workers 4 --bind 0.0.0.0:8000

# Windows
waitress-serve --port=8000 app:app
```

### 14.2 Variables d'environnement (prod)

```
YMMO_ENV=production
YMMO_SECRET_KEY=<32 octets aléatoires>
YMMO_DATABASE_URI=postgresql+psycopg2://user:pass@host:5432/ymmo
```

### 14.3 Migrations BDD

```bash
flask db init                # une seule fois
flask db migrate -m "message"
flask db upgrade
```

(Flask-Migrate est initialisé dans `create_app()`.)

### 14.4 Sonde de healthcheck

`GET /api/health` renvoie `200 ok` si la BDD répond, `503 degraded` sinon. À brancher dans Kubernetes `livenessProbe` / load-balancer health check.

---

## 15. Choix techniques et justifications

| Choix | Pourquoi |
|-------|----------|
| **Flask** plutôt que Django | minimaliste, factory pattern + blueprints donnent la même structure que Django sans le overhead. Sujet pédagogique : on voit **toutes** les couches sans magie. |
| **Pas de framework JS** (React/Vue/Svelte) | KISS. 95 % du site est en lecture, le rendu serveur est plus rapide, accessible et SEO-friendly. JS = 150 lignes, défer, optionnel. |
| **CSS vanilla** (pas de Tailwind / Bootstrap) | Une seule feuille de style maîtrisée, pas de bundling, pas de JIT, pas de classes utilitaires illisibles dans le HTML. Direction artistique unique (papier crème + terre cuite, typographie éditoriale). |
| **SQL textuel** pour les requêtes complexes | Démontre la maîtrise du SQL avancé exigée par le brief, et reste portable Postgres. L'ORM est utilisé pour le CRUD simple. |
| **scikit-learn LinearRegression** | Suffisant pour la démo : R²≈0.83, modèle interprétable, score affiché à l'utilisateur (transparence). En prod on basculerait sur XGBoost/LightGBM avec validation croisée. |
| **SQLite par défaut** | Démarrage en 1 commande, zéro config. Compatible Postgres via `YMMO_DATABASE_URI`. Aucune query Postgres-incompatible (sauf `julianday()` à porter). |
| **Charts SVG faits main** | Zéro dépendance frontend. Macro Jinja `line_chart()` réutilisable. Plus léger qu'inclure Chart.js (~80 ko). |
| **Leaflet** pour la carte | Gratuit, sans clé API, OpenStreetMap = pas de tracking utilisateur. Chargé uniquement sur la fiche bien. |
| **Comparateur en JS pur** (sessionStorage) | Aucune table DB, aucun appel serveur pour la sélection. Le serveur ne sert que la page de comparaison sur `?ids=1,2,3`. |
| **Flask-Babel** (pas de Lokalise / Crowdin) | Standard Python, fichiers `.po` versionnables, workflow CI-friendly. |
| **AnalyticsService dans `app.extensions`** | Singleton **partagé** par tous les blueprints, instancié une seule fois par app. Avant : un singleton module-level dans **chaque** blueprint = gaspillage mémoire + risques de désynchro entre workers WSGI. |
| **Helper `_time.utcnow()`** | `datetime.utcnow()` est déprécié en Python 3.12+. On centralise pour pouvoir migrer vers `DateTime(timezone=True)` sans toucher au reste de l'app. |

---

## 16. Roadmap d'évolution

- recherche géolocalisée (rayon X km depuis une adresse) — coordonnées déjà en BDD
- notifications email (visites, transactions, alertes) via Celery + Redis
- authentification SSO d'entreprise (Active Directory côté INFRA)
- modèle ML plus riche : gradient boosting + features externes (taux d'intérêt, DPE marché, distance écoles)
- mode hors-ligne PWA (Service Worker + cache des fiches consultées)
- application mobile React Native consommant l'API existante
- statistiques temps réel via Server-Sent Events (`/api/events`)

---

## Annexes

### A. Stack en chiffres

- ~6 500 lignes de code Python (services, repos, blueprints, models, analytics, tests)
- ~3 200 lignes de templates Jinja2
- ~1 150 lignes de CSS
- ~150 lignes de JS
- 385 entrées de traduction
- 19 commits Git
- 20 tests pytest, **20 / 20** passent

### B. Couverture du brief Ynov

| Exigence brief | Implémentation |
|----------------|----------------|
| Trois rôles (visiteur / client / agent / admin) | `UserRole` + `@role_required` |
| CRUD biens avec photos | `PropertyService` + `attach_images` (avec rapport d'erreurs) |
| Recherche multi-critères paginée | `PropertyRepository.search` + `PropertySearchForm` |
| Demandes de visite | `VisitRequest` + workflow Pending → Confirmed → Done |
| Suivi transactions | `Transaction` + workflow Offer → Compromise → Signed + timeline UI |
| Tableaux de bord et statistiques | `MarketAnalysis` + page `/marche` (9 sections) |
| Analyse de données | pandas + numpy dans `ymmo/analytics/` |
| Anticipation des évolutions du marché | `price_trend` (6 mois) + `monthly_revenue_chart` |
| Aide à la décision | `best_zones_to_invest` + `agent_ranking` + `anomalies` |
| Prédictions de vente | `PricePredictor` + `estimate_days_to_sell` |
| Données ouvertes / API | API JSON publique (`/api/properties`, `/api/dashboard`, `/api/estimate`) |
| Internationalisation | Flask-Babel FR/EN, 385 entrées |
| Sécurité (CSRF, hashing, sessions, rate-limit) | Flask-WTF + Werkzeug + Flask-Limiter |
| Accessibilité | WCAG AA, ARIA, focus visible, prefers-reduced-motion |
| Responsive | Mobile-first, breakpoints 600/900/1100 px |
| POO + SOLID/DRY/KISS | Architecture en couches + macros + JS minimal |
| SQL avancé | Requêtes textuelles paramétrées avec agrégations, HAVING, julianday |

---

*Documentation rédigée pour la soutenance UF B2 — Ynov Informatique.*
