# Guide de défense orale — Ymmo

Document de préparation à la soutenance : comment expliquer la conception et la structure du code, et comment répondre aux questions probables du jury.

> Objectif : être capable de parler de **n'importe quel fichier** du projet en sachant pourquoi il existe, ce qu'il fait et comment il s'articule avec le reste.

---

## Sommaire

1. [La phrase d'ouverture](#1-la-phrase-douverture)
2. [Le tour du code, dans l'ordre où je le lirais](#2-le-tour-du-code-dans-lordre-où-je-le-lirais)
3. [Le cheminement complet d'une requête](#3-le-cheminement-complet-dune-requête)
4. [Décortiquer chaque couche](#4-décortiquer-chaque-couche)
5. [Les morceaux à savoir expliquer par cœur](#5-les-morceaux-à-savoir-expliquer-par-cœur)
6. [Questions probables du jury et réponses](#6-questions-probables-du-jury-et-réponses)
7. [Vocabulaire à employer](#7-vocabulaire-à-employer)
8. [Démo : enchaînement des clics](#8-démo--enchaînement-des-clics)

---

## 1. La phrase d'ouverture

> *« Le projet est une application Flask qui couvre les trois rôles demandés — client, agent, admin — autour d'un domaine immobilier. J'ai construit le code en quatre couches : modèle, repository, service, blueprint. C'est volontaire : ça force chaque fichier à n'avoir qu'une responsabilité, et ça permet de tester le métier sans passer par HTTP. À côté, il y a un module d'analyse de données en pandas qui produit le tableau de bord du marché, et un modèle scikit-learn entraîné sur le portefeuille pour l'estimateur de prix. »*

Cette phrase pose tout en 30 secondes. Tu peux ensuite enchaîner sur n'importe quoi.

---

## 2. Le tour du code, dans l'ordre où je le lirais

Quand on tombe sur un projet Flask qu'on ne connaît pas, on l'ouvre **dans cet ordre** :

```
1. app.py                ← point d'entrée
2. config.py             ← comment l'app est paramétrée
3. ymmo/__init__.py      ← factory : c'est là que tout se branche
4. ymmo/extensions.py    ← les instances singletons (db, login, etc.)
5. ymmo/models/          ← le domaine métier (entités + enums)
6. ymmo/repositories/    ← accès BDD
7. ymmo/services/        ← logique métier
8. ymmo/blueprints/      ← routes HTTP
9. ymmo/templates/       ← rendu
10. ymmo/static/         ← CSS / JS
11. tests/               ← preuve que ça marche
```

Si tu veux convaincre, suis cet ordre quand tu présentes. Tu rentres du **plus général au plus spécifique**, et tu n'as jamais besoin de revenir en arrière.

---

## 3. Le cheminement complet d'une requête

Prenons un exemple précis : **un client clique sur "Demander une visite" sur la fiche bien**.

```
1. Le navigateur envoie  GET  /espace-client/visite/42
                         ↓
2. Flask matche la route via le blueprint « client_bp »
   définie dans ymmo/blueprints/client.py :
       @client_bp.route("/visite/<int:property_id>", methods=["GET", "POST"])
       @role_required(UserRole.CLIENT, UserRole.ADMIN)
       def request_visit(property_id):
                         ↓
3. Le décorateur @login_required (sur before_request du blueprint) vérifie
   la session : pas connecté → redirect vers /auth/connexion
                         ↓
4. @role_required vérifie current_user.role : pas client → 403
                         ↓
5. La fonction view appelle PropertyRepository.get(42)
   (couche repository : c'est l'ORM SQLAlchemy)
                         ↓
6. On instancie le formulaire VisitRequestForm (WTForms)
   Si POST : form.validate_on_submit() vérifie CSRF + champs requis
                         ↓
7. Si valide : on appelle PropertyService.request_visit(...)
   (couche service : c'est ELLE qui contient la règle métier
    "seul un client peut demander une visite")
                         ↓
8. Le service crée un VisitRequest, l'ajoute à db.session, commit.
                         ↓
9. flash("Votre demande de visite a bien été envoyée.", "success")
   + redirect vers /espace-client/
                         ↓
10. Le dashboard re-render avec le flash en haut
    + la nouvelle visite dans le tableau "Mes demandes"
```

**Ce qu'il faut savoir dire :** « Chaque couche ne fait qu'**une chose**. Le blueprint orchestre l'HTTP. Le service décide. Le repository accède aux données. Le modèle décrit le domaine. Si je changeais Flask pour FastAPI, je n'aurais qu'à réécrire les blueprints. »

---

## 4. Décortiquer chaque couche

### 4.1 `app.py` — le point d'entrée

```python
from dotenv import load_dotenv
load_dotenv()                # AVANT l'import config
from ymmo import create_app
app = create_app()
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
```

**Ce que tu dois pouvoir dire :**
- `load_dotenv()` doit être appelé **avant** l'import de `config.py`, parce que `config.py` lit `os.environ` au moment de l'import. Si tu charges `.env` après, c'est trop tard.
- En prod, on ne lance pas `python app.py` mais `gunicorn app:app` ou `waitress-serve app:app`. La variable `app` est le **callable WSGI** que ces serveurs consomment.

### 4.2 `config.py` — configuration par environnement

```python
class BaseConfig:
    SECRET_KEY = os.environ.get("YMMO_SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("YMMO_DATABASE_URI", "sqlite:///...")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # ...

class DevelopmentConfig(BaseConfig): DEBUG = True
class TestingConfig(BaseConfig): SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:" ...
class ProductionConfig(BaseConfig): SESSION_COOKIE_SECURE = True
```

**À dire :** « Pattern de configuration par environnement. La même base, surchargée pour dev / test / prod. En tests, j'utilise SQLite en mémoire pour que pytest ne touche pas mon fichier de dev. En prod, j'active `SESSION_COOKIE_SECURE` qui force HTTPS sur le cookie de session. »

### 4.3 `ymmo/__init__.py` — la factory Flask

```python
def create_app(config_class=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)
    if not app.config.get("TESTING"):
        limiter.init_app(app)

    _setup_logging(app)
    _install_request_logging(app)

    app.extensions["analytics"] = AnalyticsService()   # singleton partagé

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    # ...
    return app
```

**À dire :**
- **Pourquoi factory ?** Ça évite l'état global. Je peux créer plusieurs instances avec des configs différentes (dev, tests in-memory) sans que ça interfère.
- **Pourquoi `extensions.py` séparé ?** Pour éviter les imports circulaires. Les modèles importent `db` depuis `extensions.py`, et `__init__.py` aussi. Si `db` était défini dans `__init__.py`, les modèles tireraient `__init__.py`, qui importe les modèles → boucle.
- **`app.extensions["analytics"]`** : c'est un dict prévu par Flask pour stocker des services attachés à l'app. Avant, j'avais un `analytics_service = AnalyticsService()` au niveau module dans **chaque** blueprint = N instances qui réentraînent le modèle N fois. Maintenant, un seul instance partagé.

### 4.4 `ymmo/extensions.py` — les instances singletons

```python
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
babel = Babel()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://", ...)
```

**À dire :** « Ce fichier ne fait que créer les objets. Ils sont reliés à l'app dans la factory via `db.init_app(app)`. C'est le pattern recommandé par Flask pour les grosses apps. »

### 4.5 `ymmo/models/` — le domaine

Exemple `models/property.py` :

```python
class PropertyType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    # ...

    @property
    def label(self) -> str:
        return {PropertyType.APARTMENT: _("Appartement"), ...}[self]


class Property(db.Model):
    __tablename__ = "properties"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(
        db.Enum(PropertyType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    # ...
    agent = db.relationship("User", back_populates="properties", foreign_keys=[agent_id])

    @property
    def price_per_sqm(self) -> float:
        return float(self.price) / self.surface if self.surface else 0.0
```

**À dire :**
- C'est de la POO : `Property` est une classe Python qui hérite de `db.Model`. Les colonnes sont déclarées comme attributs de classe.
- Les **enums** ferment les valeurs possibles. C'est l'**Open/Closed principle** : si on veut ajouter "Loft", on ajoute une valeur à l'enum sans toucher au reste.
- **`values_callable`** est critique : par défaut SQLAlchemy stocke le nom du membre (`'APARTMENT'`), mais mes requêtes SQL natives comparent à `'apartment'`. Sans ce paramètre, les `WHERE type = 'apartment'` ne renvoient rien. J'ai galéré là-dessus.
- Les **properties calculées** (`price_per_sqm`, `main_image_url`, `full_name`) sont du Python pur, pas en BDD. Si la formule change, on touche un seul endroit.
- Les **relationships** (`back_populates`) déclarent les liens entre tables. SQLAlchemy en déduit les JOIN automatiques quand j'accède à `prop.agent.full_name`.

### 4.6 `ymmo/repositories/` — accès BDD

Deux styles **cohabitent** dans le même fichier :

**ORM pour le CRUD simple :**
```python
@staticmethod
def get(property_id: int) -> Property | None:
    return db.session.get(Property, property_id)
```

**SQL textuel pour les requêtes complexes :**
```python
@classmethod
def search(cls, criteria: PropertySearchCriteria) -> tuple[list[Property], int]:
    where = []
    params = {}
    if criteria.keyword:
        where.append("(LOWER(p.title) LIKE :kw OR LOWER(p.description) LIKE :kw)")
        params["kw"] = f"%{criteria.keyword.lower()}%"
    # ... tous les autres critères
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    order_sql = cls.SORTS.get(criteria.sort, cls.SORTS["recent"])

    count_sql = text(f"SELECT COUNT(*) FROM properties p {where_sql}")
    total = db.session.execute(count_sql, params).scalar_one()

    ids_sql = text(f"""
        SELECT p.id FROM properties p {where_sql}
        ORDER BY {order_sql} LIMIT :limit OFFSET :offset
    """)
    ...
```

**À dire :**
- L'ORM est nickel pour le CRUD. Mais dès qu'on veut une agrégation, des window functions, ou un tri dynamique sur 5 colonnes, écrire du SQL natif est **plus clair, plus performant, et plus proche du SQL qu'on apprend en cours**.
- **Tous** les paramètres utilisateur passent par `text(sql)` + `dict params`. **Jamais** de concaténation de chaîne (`f"WHERE id = {user_input}"`). C'est l'anti-injection SQL standard.
- Le tri (`order_sql`) est **whitelistée** dans un dict `SORTS` : impossible d'injecter `; DROP TABLE` dans le paramètre `sort`.

**Pourquoi un repository ?** Si on change SQLAlchemy pour SQLModel ou Tortoise, on ne touche **que** ce fichier. Les services et les blueprints continuent de fonctionner.

### 4.7 `ymmo/services/` — la logique métier

```python
class PropertyService:
    @staticmethod
    def request_visit(client: User, property_id: int, message: str,
                      preferred_date=None) -> VisitRequest:
        if not client.is_client:
            raise PropertyError("Seul un client peut demander une visite.")
        prop = PropertyService.get_or_404(property_id)
        visit = VisitRequest(
            property_id=prop.id, client_id=client.id,
            message=message.strip(), preferred_date=preferred_date,
            status=VisitStatus.PENDING,
        )
        db.session.add(visit)
        db.session.commit()
        return visit
```

**À dire :**
- Le service contient **les règles métier** qui n'ont rien à voir avec HTTP : "un agent ne peut éditer que ses propres biens", "un client ne peut pas demander une visite si son compte est désactivé", "un upload > 4 Mo est rejeté", etc.
- Les blueprints **n'ont pas** ces règles. Ils transforment HTTP → appel service → HTTP. Du coup mes tests peuvent appeler directement `PropertyService.request_visit(...)` sans simuler une requête HTTP.
- `PropertyError` est une exception métier dédiée. Les blueprints la capturent et flashent un message ; les tests vérifient qu'elle est levée. **Aucun raise nu** dans les services.

### 4.8 `ymmo/blueprints/` — orchestration HTTP

```python
@client_bp.route("/visite/<int:property_id>", methods=["GET", "POST"])
@role_required(UserRole.CLIENT, UserRole.ADMIN)
def request_visit(property_id: int):
    prop = PropertyRepository.get(property_id)
    if not prop: abort(404)
    form = VisitRequestForm()
    if form.validate_on_submit():
        try:
            PropertyService.request_visit(
                current_user, property_id=property_id,
                message=form.message.data, preferred_date=form.preferred_date.data,
            )
        except PropertyError as exc:
            flash(str(exc), "error")
        else:
            flash("Votre demande de visite a bien été envoyée.", "success")
            return redirect(url_for("client.dashboard"))
    return render_template("client/visit_request.html", form=form, prop=prop)
```

**À dire :**
- Le blueprint fait **3 choses** : valider l'input, appeler le service, choisir quoi rendre/rediriger.
- **Pattern PRG** (Post / Redirect / Get) : après un POST réussi, on **redirige** vers une page GET. Ça évite que le navigateur refasse la requête au refresh.
- **`@role_required`** est mon propre décorateur (dans `ymmo/decorators.py`). Il vérifie `current_user.role` et lève `abort(403)` si l'utilisateur n'a pas le bon rôle. Avantage : on lit la signature `@role_required(UserRole.AGENT)` et on comprend qui peut accéder.

### 4.9 `ymmo/forms/` — validation côté serveur

```python
class VisitRequestForm(FlaskForm):
    preferred_date = DateTimeLocalField("Date souhaitée", validators=[Optional()])
    message = TextAreaField(
        "Message",
        validators=[DataRequired(), Length(min=10, max=1000)],
    )
    submit = SubmitField("Envoyer la demande")
```

**À dire :**
- Validation **côté serveur**. On ne fait jamais confiance au navigateur. Même si le HTML5 fait du `required`, on revalide ici.
- **CSRF inclus automatiquement** par `FlaskForm` (jeton hidden dans `{{ form.csrf_token }}` ). Les `POST` sans token bon sont rejetés.
- `Meta.csrf = False` est mis explicitement sur **2** formulaires : `PropertySearchForm` (recherche en GET, le bookmark casserait sinon) et le formulaire de recherche dans les URLs. Tous les autres ont CSRF.

### 4.10 `ymmo/templates/` — rendu Jinja2

Structure hiérarchique :

```
base.html              ← layout : topbar + footer + skip-link
   ↑ extends
public/home.html       ← block content
public/detail.html
agent/dashboard.html
...
```

Macros partagées dans `_macros.html` :

```jinja
{% macro property_card(prop, anomaly_ids=None) %}
  <article class="card{% if anomaly_ids and prop.id in anomaly_ids %} card--flag{% endif %}">
    ...
  </article>
{% endmacro %}

{% macro pagination(page, pages, endpoint, args={}) %}
  ...
{% endmacro %}

{% macro line_chart(labels, series, height=240, value_format='') %}
  {# Génère un line-chart SVG sans aucune librairie externe #}
  ...
{% endmacro %}
```

**À dire :**
- `base.html` est le template de référence. Tous les autres en héritent (`{% extends "base.html" %}`).
- Les **macros** factorisent la duplication. La carte d'un bien est définie **une fois** et réutilisée sur la home, le listing, le dashboard client, etc.
- **`line_chart` est important** : c'est un graphique en SVG **fait main**, sans Chart.js ni D3. C'est ~70 lignes de Jinja qui calculent les positions et émettent un `<svg>` complet. Zéro dépendance frontend.

### 4.11 Le CSS

Une seule feuille de style `static/css/main.css` (~1150 lignes), organisée en **31 sections numérotées** :

```
1. Tokens (variables CSS)
2. Mode sombre
3. Reset léger
4. Accessibilité
5. Conteneurs et rythme
6. Typographie
7. Header / nav
8. Boutons
...
30. Compare tray + table
31. Leaflet map
```

**Variables CSS pour le thème :**
```css
:root {
    --paper:   #f7f1e7;
    --ink:     #14202b;
    --brick:   #b94a2c;
    --rule:    #e1d6c2;
}
[data-theme="dark"] {
    --paper:   #11161d;
    --ink:     #f0e6d6;
    --brick:   #e07b58;
    ...
}
```

**À dire :**
- Tout passe par des **variables CSS** (custom properties). Ça veut dire qu'il suffit de changer `[data-theme="dark"]` pour basculer **toute** l'app en sombre, sans réécrire les styles.
- `prefers-color-scheme: dark` détecte le thème système. L'utilisateur peut overrider via le bouton ◐/◑ → on stocke son choix dans `localStorage`.
- **Anti-flash** : un petit script dans le `<head>` applique `data-theme` **avant** le rendu, sinon on a un flash blanc → sombre.

### 4.12 Le JS

~150 lignes au total, **deux fichiers** :

- `main.js` : thème, mobile menu, auto-submit selects, confirm sur boutons destructifs, "tout sélectionner"
- `compare.js` : comparateur via `sessionStorage`

```javascript
// compare.js — extrait
function load()  { return JSON.parse(sessionStorage.getItem("ymmo-compare") || "[]"); }
function save(items) { sessionStorage.setItem("ymmo-compare", JSON.stringify(items)); }

document.querySelectorAll(".compare-btn").forEach(function (b) {
    b.addEventListener("click", function () {
        var id = parseInt(b.dataset.compareId, 10);
        var items = load();
        // toggle...
        save(items);
        refresh();
    });
});
```

**À dire :**
- Pas de framework. Tout est **vanilla**. Pas de bundler, pas de webpack, pas de Vite.
- **Le site marche sans JavaScript**. Si tu désactives JS dans le navigateur, tu peux toujours te connecter, chercher, demander une visite. Le JS améliore (toggle thème, comparateur, menu burger), il n'est pas **requis**.
- Le comparateur n'a **aucun backend** dédié. La sélection vit dans `sessionStorage` (donc côté client uniquement, perdue à la fermeture de l'onglet). La page `/comparer` lit `?ids=1,2,3` et rend la table côté serveur.

---

## 5. Les morceaux à savoir expliquer par cœur

Ce sont les **8 fichiers/concepts** que le jury risque de te demander d'expliquer en détail. Mémorise-les.

### 5.1 `PropertyRepository.search` (le SQL avancé)

C'est ton **meilleur exemple** de SQL dynamique sécurisé. Fichier : `ymmo/repositories/property_repository.py`.

Ce qu'il faut savoir dire :
- Construit dynamiquement la clause `WHERE` en fonction des critères du formulaire.
- **Paramètres liés** : chaque valeur utilisateur (`:kw`, `:min_price`, `:status_0`, etc.) est passée dans le dict `params`. Jamais de concaténation.
- Tri **whitelisté** : `SORTS = {"recent": "p.created_at DESC", ...}`. L'utilisateur envoie `recent` ou `price_asc`, jamais du SQL.
- **Pagination en 2 requêtes** : une `COUNT(*)` pour le total, une `SELECT id ... LIMIT :limit OFFSET :offset` pour la page courante. Ensuite, je récupère les objets ORM dans un troisième `SELECT WHERE id IN (...)` pour préserver l'ordre.
- Si on retournait directement `SELECT * FROM properties LIMIT ...`, on serait obligé de désérialiser à la main. Avec l'ORM derrière, on récupère des `Property` complets avec leurs relations.

### 5.2 `MarketAnalysis.anomalies` (la détection d'anomalies)

Fichier : `ymmo/analytics/market_analysis.py`. ~15 lignes.

```python
def anomalies(self, sigma: float = 2.0):
    grouped = self.df.groupby(["city", "type"])["price_per_sqm"].agg(["mean", "std"]).reset_index()
    merged = self.df.merge(grouped, on=["city", "type"], how="left")
    merged = merged[merged["std"].fillna(0) > 0]   # évite division par zéro
    merged["zscore"] = (merged["price_per_sqm"] - merged["mean"]) / merged["std"]
    flagged = merged[merged["zscore"].abs() >= sigma]
    ...
```

À dire :
- Z-score = (valeur − moyenne) / écart-type. Au-delà de 2σ, on est statistiquement dans les 5 % les plus extrêmes.
- Je groupe par (ville, type) parce qu'un T3 à Paris à 8000 €/m² n'est pas une anomalie, mais un T3 à Lyon à 8000 €/m² oui.
- Je filtre `std > 0` pour ne pas diviser par zéro sur des segments qui ont un seul bien.

### 5.3 `PricePredictor.fit` (le pipeline scikit-learn)

Fichier : `ymmo/analytics/price_predictor.py`.

```python
preprocessor = ColumnTransformer(transformers=[
    ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
], remainder="passthrough")
pipeline = Pipeline(steps=[("pre", preprocessor), ("reg", LinearRegression())])
pipeline.fit(x, y)
self.score = round(float(pipeline.score(x, y)), 3)   # R²
```

À dire :
- `OneHotEncoder` transforme les colonnes catégorielles (`type`, `city`) en vecteurs 0/1. Avec `handle_unknown="ignore"`, si on prédit pour une ville qu'on n'a jamais vue, le modèle ne plante pas (il met 0 sur toutes les villes).
- `remainder="passthrough"` : les colonnes non listées (surface, rooms, has_parking…) passent telles quelles.
- `LinearRegression` apprend des coefficients sur ces features.
- Le **R²** est le score affiché à l'utilisateur. C'est la part de variance expliquée par le modèle. R² = 0.83 veut dire "le modèle explique 83 % de la variance des prix". Au-delà de 0.7 on parle de modèle correct pour de la démo.
- **Pourquoi régression linéaire et pas XGBoost ?** Parce que c'est interprétable, ça suffit pour un MVP, et le brief demande "des analyses", pas le state-of-the-art. En prod je passerais sur du gradient boosting.

### 5.4 `AnalyticsService.estimate_days_to_sell` (la prédiction de vente)

Fichier : `ymmo/services/analytics_service.py`.

```python
def estimate_days_to_sell(self, prop):
    base = sales_velocity[prop.type.value]   # durée moyenne pour ce type
    comparable = PropertyRepository.comparable_stats(prop.city, prop.type.value)
    ref = comparable["avg_price_sqm"]
    delta = (float(prop.price)/float(prop.surface) - ref) / ref
    coeff = max(0.4, min(1.0 + delta * 3.0, 2.5))   # clamp
    days = max(7, int(round(base * coeff)))
    ...
```

À dire :
- C'est une **heuristique**, pas un modèle ML. Je combine la durée moyenne historique pour ce type, et un coefficient lié à l'écart de prix vs marché local.
- +10 % vs marché → coeff ≈ 1.3 (30 % plus lent). −10 % → coeff ≈ 0.7. C'est **borné** [0.4, 2.5] pour pas avoir des prédictions absurdes.
- Affiché sur la fiche bien avec un tag indiquant l'écart vs marché.

### 5.5 La sécurité (CSRF + rate-limit)

À dire :
- **CSRF** : `Flask-WTF` génère un token aléatoire par session, injecté dans `{{ form.csrf_token }}`. À la soumission, le serveur compare. Sans token, 400. C'est ça qui bloque l'attaque où un site malveillant fait soumettre un formulaire vers mon app au nom du visiteur.
- **Rate-limit** : `Flask-Limiter` compte les requêtes par IP. `@limiter.limit("5 per minute")` sur le login bloque le bruteforce. Au-delà, 429 avec une page dédiée.
- **Sessions HttpOnly** : le JavaScript ne peut pas lire le cookie de session. Ça bloque l'exfiltration via XSS.
- **SameSite Lax** : le cookie n'est pas envoyé lors d'une navigation cross-site (sauf top-level GET). Anti-CSRF de seconde ligne.
- **Hashing PBKDF2-SHA256** : Werkzeug. Salt aléatoire automatique. Pas de bcrypt ici parce que stdlib + Werkzeug suffit pour le sujet.

### 5.6 Le décorateur `@role_required`

Fichier : `ymmo/decorators.py` (~15 lignes).

```python
def role_required(*roles: UserRole):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

À dire :
- C'est un **décorateur paramétré** : `role_required(UserRole.AGENT, UserRole.ADMIN)` retourne le vrai décorateur.
- Avantage : sur n'importe quelle route je peux ajouter `@role_required(...)` et la doc est dans la signature. Plus lisible que de vérifier le rôle dans le corps de chaque fonction.

### 5.7 Le seed `seed.py`

Ce qu'il fait :
1. `db.drop_all() + db.create_all()` → wipe et recrée les tables
2. Insère 13 agences (1 siège + 12), avec leur (lat, lng)
3. Insère un admin, des agents (1-2 par agence), 20+ clients
4. Insère 120 biens aléatoires mais cohérents (types pondérés, surfaces logiques, prix corrélés à la ville)
5. Insère des favoris, demandes de visite, transactions

À dire :
- `random.seed(42)` : reproductibilité. À chaque exécution on a la même base.
- Les coordonnées de chaque ville ont un **jitter aléatoire** de ±0.015° (~1.5 km) pour que les marqueurs Leaflet ne soient pas tous superposés au centre-ville.
- Le seed s'exécute **dans un `test_request_context`** parce que Flask-Babel a besoin d'un contexte HTTP pour résoudre `gettext()` (utilisé dans `PropertyType.label`).

### 5.8 Les tests

Fichier `tests/conftest.py` :

```python
@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()
```

À dire :
- `TestingConfig` utilise `sqlite:///:memory:` → la BDD est en RAM, recréée pour chaque test.
- `db.create_all() / drop_all()` autour de `yield` garantit qu'aucun test ne pollue les autres (isolation).
- 20 tests couvrent : auth (5), recherche (4), analytics (4), pages (7). Tous passent en ~4 secondes.

---

## 6. Questions probables du jury et réponses

### Architecture

**Q : Pourquoi Flask et pas Django ?**
> *« Flask est minimaliste, on voit toutes les couches. Django apporte beaucoup de magie (admin auto, ORM intégré, signals…) qui cache la mécanique. Pour un projet pédagogique où je dois prouver que je comprends ce qui se passe, Flask est plus adapté. Le factory pattern + blueprints me donne la même modularité que Django sans le overhead. »*

**Q : Pourquoi séparer repository et service ?**
> *« Le repository ne fait que parler à la BDD. Le service contient les règles métier. Si demain je migre de SQLAlchemy à un autre ORM, je ne touche qu'aux repositories. Si je veux exposer la même logique via une CLI ou un job batch, j'appelle les services sans passer par les blueprints. Ça respecte le Single Responsibility Principle. »*

**Q : Pourquoi pas un framework JS (React, Vue) ?**
> *« 95 % du site est en lecture. Un rendu serveur est plus rapide (pas de hydration), plus accessible (le HTML est complet dès la première réponse), meilleur pour le SEO, et utilisable sans JavaScript. Mon JS fait 150 lignes. Avec React j'aurais ajouté 200 ko de bundle pour rendre le même HTML. »*

**Q : Pourquoi SQLite et pas Postgres ?**
> *« SQLite démarre en une commande, zéro config — parfait pour la démo et les tests. Mon code est compatible Postgres via la variable d'env `YMMO_DATABASE_URI`. La seule fonction SQLite-spécifique est `julianday()` dans `kpis()`, qui se porte en `EXTRACT(EPOCH FROM …)/86400` en Postgres. Trois lignes à toucher. »*

### Sécurité

**Q : Comment tu te protèges contre l'injection SQL ?**
> *« Tous les paramètres utilisateur passent par des paramètres liés : `text(sql)` + dict `params`. Jamais de f-string ni de concaténation. Même pour les listes (statuts par exemple) je génère des bind dynamiques `:status_0, :status_1, ...`. Le tri est whitelistée dans un dict pour qu'on ne puisse pas injecter via le paramètre `sort`. »*

**Q : Et contre XSS ?**
> *« Jinja2 échappe par défaut. Je n'utilise nulle part `|safe` ni `Markup(...)`. Le seul endroit où j'inclus du contenu utilisateur dans une chaîne stockée en BDD est l'`alt_text` des photos, et là je l'escape via `markupsafe.escape(prop.title)[:200]` avant le commit. »*

**Q : Bruteforce sur le login ?**
> *« Flask-Limiter, 5 tentatives par minute par IP. Au-delà : 429. J'ai aussi limité l'inscription à 3 par minute pour empêcher la création massive de comptes. La limite globale par défaut est 1000 req/h/IP. En prod on pointerait `storage_uri` vers Redis pour partager les compteurs entre workers. »*

**Q : Comment tu stockes les mots de passe ?**
> *« PBKDF2-SHA256 via `werkzeug.security.generate_password_hash`. Salt aléatoire automatique. Je vérifie avec `check_password_hash`. Mot de passe minimum 8 caractères validé côté serveur dans `AuthService.register`. »*

### Données et ML

**Q : Comment tu nettoies tes données ?**
> *« Dans `build_property_dataframe` : je convertis les colonnes numériques avec `pd.to_numeric(errors="coerce")` qui transforme les invalides en NaN, je drop les lignes où `price` ou `surface` est NaN ou ≤ 0, je strippe les préfixes Enum, et je calcule `price_per_sqm` une fois pour toutes. Le DataFrame retourné est sain pour toutes les analyses en aval. »*

**Q : Ton modèle vaut R² = 0.83. C'est bon ?**
> *« Pour un MVP avec un dataset de seed, c'est correct. Ça veut dire qu'on explique 83 % de la variance des prix avec une régression linéaire sur (surface, rooms, type, city, équipements). En production je basculerais sur XGBoost ou LightGBM, avec validation croisée k-fold pour vérifier que le modèle ne sur-apprend pas. Et j'ajouterais des features externes : taux d'intérêt, DPE, proximité écoles. »*

**Q : Pourquoi détection d'anomalies à 2σ et pas 3σ ?**
> *« 2σ = environ 5 % des biens flaggés, c'est le bon compromis pour qu'un agent voie quelque chose d'actionnable sur son tableau de bord. À 3σ on ne flaggerait quasi rien (0.3 % théorique). Le seuil est paramétrable dans la fonction. »*

**Q : Comment marche ta prédiction du délai de vente ?**
> *« C'est une heuristique, pas un modèle ML. Je prends la durée moyenne historique du cycle pour ce type de bien (calculée sur les transactions signées), et je la multiplie par un coefficient lié à l'écart de prix vs marché local. +10 % de prix vs moyenne → 30 % plus lent. Je clampe entre 0.4 et 2.5 pour ne pas avoir des prédictions absurdes. C'est explicable au client : on ne cache pas la logique. »*

### Accessibilité / qualité

**Q : Comment tu garantis l'accessibilité ?**
> *« HTML5 sémantique : main, nav, aside, article, address. ARIA : aria-label, aria-live sur les flashes, aria-current sur la pagination. Skip-link en haut visible au focus. Focus visible 2 px avec une couleur contrastée. Contrastes vérifiés ≥ 4.5:1. Mode sombre via prefers-color-scheme. Animations désactivées si prefers-reduced-motion. Et j'ai testé la navigation entière au clavier. »*

**Q : Mobile ?**
> *« Mobile-first. Une seule feuille de style, breakpoints à 600 / 900 / 1100 px. Navigation hamburger sous 960 px. Tous les boutons sont à hauteur minimum 44 px (taille tactile recommandée par Apple HIG). »*

**Q : Performance ?**
> *« CSS unique d'environ 30 ko, JS d'environ 10 ko, tout en defer. Pas de framework. Images en loading="lazy" avec aspect-ratio pour éviter le layout shift. Leaflet chargé uniquement sur la fiche bien, pas sur les autres pages. »*

### Internationalisation

**Q : Comment marche l'i18n ?**
> *« Flask-Babel. Les chaînes du code sont wrappées en `_("...")` et `ngettext(...)` pour les pluriels. La commande `pybabel extract` me génère un `messages.pot`, que je traduis dans `messages.po`. La commande `pybabel compile` produit le `messages.mo` binaire utilisé au runtime. Le sélecteur de locale lit d'abord le cookie `ymmo_lang`, sinon `Accept-Language`, sinon FR. Le switcher FR/EN dans la topbar poste sur `/lang` et set le cookie pour un an. »*

### Tests

**Q : Pourquoi seulement 20 tests ?**
> *« J'ai testé les fonctions critiques : auth, recherche multi-critères, agrégations SQL, pipeline analytics, et un test smoke par page publique. Ça couvre les chemins métiers importants. Pour du test de pixel-perfect UI ou des stress-tests de charge, ce serait Playwright et k6, c'est hors-scope pour ce projet. »*

**Q : Tu testes en SQLite. Et si ça marche pas en Postgres ?**
> *« Bonne question. Le risque réel est sur `julianday()`. Je l'isolerais dans un helper de repository et j'aurais un test paramétré qui tourne sur les deux moteurs en CI. Pour ce projet, j'ai choisi de rester sur SQLite pour la simplicité de déploiement de la démo. »*

### Choix tactiques

**Q : Pourquoi 4 couches et pas 2 ou 6 ?**
> *« 2 couches (vue + tout-le-reste-en-un-fichier) c'est ce que font les tutos Flask de 30 minutes. Ça scale pas : à 3000 lignes c'est ingérable. 6 couches (DTOs, façades, sous-services…) c'est du sur-engineering pour un projet d'école. 4 couches — modèle, repository, service, blueprint — c'est ce que je vois dans la majorité des projets Flask sérieux. C'est testable, lisible, et chaque couche a une responsabilité claire. »*

**Q : Tu n'as pas peur que ton singleton AnalyticsService devienne un goulot d'étranglement ?**
> *« Si on devait scaler à 1000 req/s, oui. Là le predictor est entraîné une fois, ensuite `predict_one` est O(features) — millisecondes. En cas de gros volumes, je passerais à un cache distribué (Redis) avec invalidation explicite sur CRUD bien, ou à un service ML séparé exposé via gRPC. »*

**Q : Pourquoi Leaflet et pas Google Maps ?**
> *« Leaflet est gratuit, sans clé API, et utilise OpenStreetMap qui ne track pas les utilisateurs. Pour Google Maps il faut une clé API, un budget, et accepter le tracking. Pour un projet pédagogique c'est un non-départ. »*

---

## 7. Vocabulaire à employer

Petits mots qui font la différence quand tu parles :

- "**Pattern factory**" plutôt que "fonction qui crée l'app"
- "**Couche de présentation / métier / accès données**" plutôt que "le HTML / le code / la BDD"
- "**Single Responsibility Principle**" plutôt que "chaque fichier fait une chose"
- "**Inversion de dépendances**" pour parler du fait que tes services prennent un user en paramètre au lieu d'importer current_user
- "**Paramètres liés**" plutôt que "j'évite l'injection SQL"
- "**Form de validation côté serveur**" plutôt que "WTForms"
- "**Sanitisation**" plutôt que "j'escape"
- "**Idempotent**" pour qualifier une route qui peut être appelée plusieurs fois sans effet de bord (`GET`, `DELETE`)
- "**Cache miss**" / "**Cache hit**" pour parler de ton predictor qui se réentraîne ou pas
- "**Lazy loading**" pour parler de `loading="lazy"` sur les images
- "**Sémantique HTML5**" plutôt que "j'utilise les bonnes balises"
- "**Mobile-first**" plutôt que "ça marche sur téléphone"
- "**Health check**" plutôt que "l'endpoint qui dit si ça marche"
- "**WCAG AA**" plutôt que "accessible"

---

## 8. Démo : enchaînement des clics

Voici l'ordre exact qui montre **tout** en 4-5 minutes. Apprends-le par cœur.

```
1.  http://127.0.0.1:5000/         (Accueil)
    → Pointer : "barre de recherche dans le hero", "3 sections numérotées",
      basculer FR↔EN (montrer que ça change tout le site),
      basculer thème clair↔sombre

2.  Cliquer "Voir les biens"       (/biens)
    → Pointer : "rail de filtres en sticky", appliquer un filtre
      ville=Lyon + type=appartement → moins de résultats
    → Sur une carte, cliquer "⊕ Comparer" sur 2 biens
    → Pointer : le drawer flottant en bas qui apparaît avec les 2 biens

3.  Cliquer "Comparer"             (/comparer?ids=...)
    → Pointer : table côte à côte, "ça vit dans sessionStorage,
      aucun appel serveur pour la sélection"

4.  Retour catalogue, cliquer un bien   (/biens/<id>)
    → Pointer : galerie 1+4 type Airbnb, caractéristiques,
      "Délai estimé pour vendre : X jours" (la prédiction),
      carte Leaflet, contact agent

5.  Cliquer "Marché" dans la nav    (/marche)
    → Pointer : courbe CA mensuel SVG, courbe tendance prix 6 mois,
      tableau des zones d'opportunité, vélocité par type

6.  Cliquer "Estimer"               (/estimer)
    → Remplir : type=appartement, ville=Lyon, surface=60, rooms=3
    → Soumettre → "estimation : X €, R² = 0.83"
    → Pointer : "le R² est le score du modèle, on l'affiche pour la
      transparence"

7.  Se connecter en agent           (agent@ymmo.fr / agent12345)
    → /espace-agent/
    → Pointer : KPI avec anomalies, courbe CA mensuel, portefeuille
      paginé avec recherche, action groupée
    → Cliquer sur le ♥ d'un bien → /biens/<id>/favoris
      "Vue agent : qui a mis mon bien en favori"

8.  Cliquer "📅 Calendrier"         (/espace-agent/calendrier)
    → Pointer : grille 7 jours, navigation semaine ±

9.  Cliquer "⤓ Export CSV"          (téléchargement)
    → Ouvrir le CSV pour montrer

10. Se déconnecter, se connecter admin   (admin@ymmo.fr / admin12345)
    → /admin/
    → Pointer : ranking des agents, recherche par nom/email,
      filtre par rôle, exports CSV transactions

11. Tester /api/health              (terminal ou Postman)
    → curl http://127.0.0.1:5000/api/health
    → Pointer : "endpoint standard pour orchestrateurs"

12. Tester /api/properties avec headers
    → curl -D - http://127.0.0.1:5000/api/properties?per_page=3
    → Pointer : X-Total-Count, X-Page, X-RateLimit-*
```

**Si on te coupe à 3 minutes :** garde au minimum 1, 2, 4, 7 et 10. C'est le squelette qui montre client + agent + admin + data + ML.

---

## Conclusion

Si tu retiens **trois choses** :

1. **L'architecture en couches** est ton fil rouge. Tu peux y revenir à chaque question : "ça vit dans la couche service parce que c'est une règle métier, pas une question HTTP".

2. **Le SQL paramétré, le R², le Z-score, et le pattern factory** sont les quatre concepts techniques qui doivent sortir naturellement quand on te questionne.

3. **Tout est justifié.** Chaque choix (SQLite, vanilla JS, scikit-learn, Leaflet, Flask) a une raison. Si tu doutes, dis "**j'ai privilégié la lisibilité et la maîtrise du code à la performance théorique**" — ça passe partout pour un projet pédagogique.

Bonne soutenance.
