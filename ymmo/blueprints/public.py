"""Pages publiques : accueil, recherche, fiche bien, estimation."""

from __future__ import annotations

from flask import Blueprint, abort, make_response, redirect, render_template, request

from ..forms import PriceEstimationForm, PropertySearchForm
from ..models import PropertyType
from ..repositories import PropertyRepository
from ..repositories.property_repository import PropertySearchCriteria
from ..services import AnalyticsService, PropertyService

public_bp = Blueprint("public", __name__)
analytics_service = AnalyticsService()


@public_bp.route("/")
def home():
    featured = PropertyRepository.top_viewed(limit=6)
    cities = PropertyRepository.avg_price_per_city(limit=6)
    # On garde la barre de recherche du hero auto-suffisante : on lui passe
    # la liste des villes pour le <select>, et un récap chiffré pour l'aside.
    nav_cities = sorted({c["city"] for c in PropertyRepository.avg_price_per_city(limit=50)})
    by_status = PropertyRepository.count_by_status()
    stats = {
        "total": sum(by_status.values()),
        "available": by_status.get("available", 0),
        "cities": len(nav_cities),
    }
    return render_template(
        "public/home.html",
        featured=featured,
        cities=cities,
        nav_cities=nav_cities,
        stats=stats,
    )


@public_bp.route("/biens")
def list_properties():
    form = PropertySearchForm(request.args, meta={"csrf": False})
    page = max(1, request.args.get("page", default=1, type=int))

    criteria = PropertySearchCriteria(
        keyword=form.keyword.data or None,
        city=form.city.data or None,
        property_type=PropertyType(form.property_type.data) if form.property_type.data else None,
        min_price=float(form.min_price.data) if form.min_price.data is not None else None,
        max_price=float(form.max_price.data) if form.max_price.data is not None else None,
        min_surface=float(form.min_surface.data) if form.min_surface.data is not None else None,
        min_rooms=int(form.min_rooms.data) if form.min_rooms.data is not None else None,
        has_parking=bool(form.has_parking.data),
        has_garden=bool(form.has_garden.data),
        sort=form.sort.data or "recent",
        page=page,
    )
    items, total = PropertyService.search(criteria)
    pages = max(1, -(-total // criteria.per_page))

    return render_template(
        "public/list.html",
        form=form,
        items=items,
        total=total,
        page=page,
        pages=pages,
        sort=criteria.sort,
    )


@public_bp.route("/biens/<int:property_id>")
def property_detail(property_id: int):
    try:
        prop = PropertyService.view(property_id)
    except Exception:
        abort(404)
    return render_template("public/detail.html", prop=prop)


@public_bp.route("/estimer", methods=["GET", "POST"])
def estimate():
    form = PriceEstimationForm(request.form if request.method == "POST" else None)
    result = None
    error = None
    if request.method == "POST" and form.validate():
        try:
            result = analytics_service.predict_price(
                {
                    "type": form.type.data,
                    "city": form.city.data,
                    "surface": float(form.surface.data),
                    "rooms": int(form.rooms.data),
                    "bedrooms": int(form.bedrooms.data or 0),
                    "bathrooms": int(form.bathrooms.data or 0),
                    "has_parking": form.has_parking.data,
                    "has_garden": form.has_garden.data,
                    "has_balcony": form.has_balcony.data,
                }
            )
        except RuntimeError as exc:
            error = str(exc)
    return render_template("public/estimate.html", form=form, result=result, error=error)


@public_bp.route("/marche")
def market():
    dashboard = analytics_service.dashboard()
    return render_template("public/market.html", dashboard=dashboard)


@public_bp.route("/agences")
def agencies():
    from ..repositories import AgencyRepository

    return render_template("public/agencies.html", agencies=AgencyRepository.list_all())


@public_bp.post("/lang")
def set_language():
    """Change la langue via cookie (1 an), redirige vers la page d'origine."""
    code = (request.form.get("lang") or "").lower()
    if code not in ("fr", "en"):
        code = "fr"
    target = request.referrer or request.url_root
    response = make_response(redirect(target))
    response.set_cookie(
        "ymmo_lang", code, max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=False
    )
    return response
